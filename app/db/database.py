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

from app.core.skills_taxonomy import check_skill_match, calculate_weighted_fit, normalize_skill
from app.services.title_utils import get_title_search_parameters

def is_skill_match(cand_skill: str, job_skill: str) -> bool:
    """Check if candidate skill matches job required skill using taxonomy & fuzzy rules."""
    return check_skill_match(cand_skill, job_skill)


async def fetch_live_jobs_by_skills(
    user_skills: List[str],
    target_title: Optional[str] = None,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetch live jobs matching a candidate's CV skills and target career title.
    Employs multi-tier title search, negative domain filtering, and taxonomy skill matching.
    """
    global _pool
    if _pool is None:
        await init_db_pool()

    if _pool is None:
        return []

    clean_user_skills = [s.strip() for s in user_skills if s and len(s.strip()) > 0]
    fuzzy_skills = [f"%{s}%" for s in clean_user_skills[:15]]

    clean_title, core_keywords, neg_keywords = get_title_search_parameters(target_title)
    
    fuzzy_title = f"%{clean_title}%" if clean_title else "%"
    
    # Create keyword patterns for multi-tier matching
    kw1 = f"%{core_keywords[0]}%" if len(core_keywords) > 0 else "%"
    kw2 = f"%{core_keywords[1]}%" if len(core_keywords) > 1 else "%"

    # SQL query with multi-tier title priority and skill fallback
    query = """
        SELECT
            job_id, title, company, location, country,
            work_arrangement, date_posted, job_link,
            source, required_skills, skills_json,
            min_salary, max_salary
        FROM "IT_jobs"."IT"
        WHERE
            ($2 <> '%' AND title ILIKE $2)
            OR ($3 <> '%' AND $4 <> '%' AND title ILIKE $3 AND title ILIKE $4)
            OR ($3 <> '%' AND title ILIKE $3)
            OR (array_length($1::text[], 1) IS NOT NULL AND required_skills ILIKE ANY ($1::text[]))
        ORDER BY 
            CASE WHEN $2 <> '%' AND title ILIKE $2 THEN 3
                 WHEN $3 <> '%' AND $4 <> '%' AND title ILIKE $3 AND title ILIKE $4 THEN 2
                 WHEN $3 <> '%' AND title ILIKE $3 THEN 1
                 ELSE 0 END DESC,
            date_posted DESC
        LIMIT 100
    """

    try:
        async with _pool.acquire() as conn:
            records = await conn.fetch(query, fuzzy_skills, fuzzy_title, kw1, kw2)

        scored_jobs = []
        target_title_lower = target_title.lower() if target_title else ""
        clean_title_lower = clean_title.lower() if clean_title else ""

        for rec in records:
            job_dict = dict(rec)
            job_title_lower = (job_dict.get("title") or "").lower()

            # Domain Negative Exclusion Filter
            if any(neg in job_title_lower for neg in neg_keywords):
                continue

            req_skills_raw = job_dict.get("required_skills") or ""
            job_skills = [s.strip() for s in req_skills_raw.split(",") if s.strip()]

            matched = []
            missing = []

            for js in job_skills:
                is_matched = any(check_skill_match(us, js) for us in clean_user_skills)
                if is_matched:
                    matched.append(js)
                else:
                    missing.append(js)

            # Calculate weighted skill fit percentage using taxonomy engine
            match_pct = calculate_weighted_fit(matched, job_skills)

            # Title similarity score calculation
            title_boost = 0
            if clean_title_lower:
                if clean_title_lower == job_title_lower:
                    title_boost = 2000
                elif clean_title_lower in job_title_lower or job_title_lower in clean_title_lower:
                    title_boost = 1000
                elif len(core_keywords) > 1 and all(kw.lower() in job_title_lower for kw in core_keywords):
                    title_boost = 800
                elif any(kw.lower() in job_title_lower for kw in core_keywords):
                    title_boost = 400

            # Ranking score: Title match > Weighted Skill Fit > Matched Count
            total_rank = title_boost + (match_pct * 2) + len(matched)

            job_dict["matched_skills"] = matched
            job_dict["missing_skills"] = missing
            job_dict["skill_match_percent"] = match_pct
            job_dict["_rank"] = total_rank

            scored_jobs.append(job_dict)

        # Sort by total rank score descending
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

