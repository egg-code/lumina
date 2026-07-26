import os
import asyncpg
import re
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Connection settings
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback credentials provided by user
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "it_jobs")
DB_USER = os.getenv("DB_USER", "user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

_pool: asyncpg.Pool = None
_pool_init_failed = False

async def init_db_pool():
    global _pool, _pool_init_failed
    if _pool is None and not _pool_init_failed:
        try:
            if DATABASE_URL:
                _pool = await asyncpg.create_pool(
                    dsn=DATABASE_URL,
                    min_size=1,
                    max_size=10
                )
                logger.info("Connected to PostgreSQL database via DATABASE_URL")
            else:
                _pool = await asyncpg.create_pool(
                    host=DB_HOST,
                    port=DB_PORT,
                    database=DB_NAME,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    min_size=1,
                    max_size=10
                )
                logger.info(f"Connected to PostgreSQL database {DB_NAME} at {DB_HOST}:{DB_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            _pool_init_failed = True

async def close_db_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

def is_skill_match(cand_skill: str, job_skill: str) -> bool:
    """Check if candidate skill matches job required skill using exact/boundary matching."""
    c_norm = cand_skill.strip().lower()
    j_norm = job_skill.strip().lower()
    if not c_norm or not j_norm:
        return False
    if c_norm == j_norm:
        return True
    if len(c_norm) > 2 and len(j_norm) > 2:
        if c_norm in j_norm or j_norm in c_norm:
            return True
    pattern = rf"\b{re.escape(c_norm)}\b"
    return bool(re.search(pattern, j_norm))


async def fetch_live_jobs_by_skills(
    user_skills: List[str],
    target_title: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetch live jobs matching a candidate's CV skills and optional target career title.
    Calculates matched skills, missing skills, and skill match score percentage.
    """
    global _pool
    if _pool is None:
        await init_db_pool()

    if _pool is None:
        return []

    clean_user_skills = [s.strip() for s in user_skills if s and len(s.strip()) > 0]
    fuzzy_skills = [f"%{s}%" for s in clean_user_skills[:15]]
    fuzzy_title = f"%{target_title.strip()}%" if target_title and target_title.strip() else "%"

    query = """
        SELECT
            job_id, title, company, location, country,
            work_arrangement, date_posted, job_link,
            source, required_skills, skills_json,
            min_salary, max_salary
        FROM "IT_jobs"."IT"
        WHERE
            (array_length($1::text[], 1) IS NOT NULL AND required_skills ILIKE ANY ($1::text[]))
            OR ($2 <> '%' AND title ILIKE $2)
        ORDER BY date_posted DESC
        LIMIT 100
    """

    try:
        async with _pool.acquire() as conn:
            records = await conn.fetch(query, fuzzy_skills, fuzzy_title)

        scored_jobs = []
        target_title_lower = target_title.lower() if target_title else ""

        for rec in records:
            job_dict = dict(rec)
            req_skills_raw = job_dict.get("required_skills") or ""
            job_skills = [s.strip() for s in req_skills_raw.split(",") if s.strip()]

            matched = []
            missing = []

            for js in job_skills:
                is_matched = any(is_skill_match(us, js) for us in clean_user_skills)
                if is_matched:
                    matched.append(js)
                else:
                    missing.append(js)

            if job_skills:
                match_pct = int((len(matched) / len(job_skills)) * 100)
            else:
                match_pct = 50

            # Title similarity score
            job_title_lower = (job_dict.get("title") or "").lower()
            title_boost = 0
            if target_title_lower:
                if target_title_lower in job_title_lower or job_title_lower in target_title_lower:
                    title_boost = 30
                elif any(word in job_title_lower for word in target_title_lower.split() if len(word) > 3):
                    title_boost = 15

            # Total ranking score prioritize number of matched skills + percentage + title fit
            total_rank = (len(matched) * 25) + match_pct + title_boost

            job_dict["matched_skills"] = matched
            job_dict["missing_skills"] = missing
            job_dict["skill_match_percent"] = match_pct
            job_dict["_rank"] = total_rank

            scored_jobs.append(job_dict)

        # Sort by total rank score descending, then date_posted
        scored_jobs.sort(
            key=lambda x: (x["_rank"], x["skill_match_percent"], len(x["matched_skills"]), x.get("date_posted") or ""),
            reverse=True
        )

        result = []
        for j in scored_jobs[:limit]:
            j.pop("_rank", None)
            result.append(j)

        return result
    except Exception as e:
        logger.error(f"Error fetching live jobs by skills: {e}")
        return []

async def fetch_live_jobs_for_title(keyword: str, limit: int = 5, user_skills: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Fetch live jobs matching a career title and optional user skills list.
    """
    return await fetch_live_jobs_by_skills(user_skills or [], target_title=keyword, limit=limit)

