import os
import asyncpg
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
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

async def fetch_live_jobs_for_title(keyword: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetch live jobs matching a career title (e.g. "Data Analyst" or "Backend Developer").

    Search strategy:
      - High-performance ILIKE / Trigram index matching on job title and required_skills.
      - Exact/prefix title matches ranked first, followed by recency (date_posted DESC).
    """
    global _pool
    if _pool is None:
        await init_db_pool()

    if _pool is None:
        return []

    query = """
        SELECT
            job_id, title, company, location, country,
            work_arrangement, date_posted, job_link,
            source, required_skills, skills_json,
            min_salary, max_salary,
            CASE WHEN title ILIKE $1 THEN 0 ELSE 1 END AS rank
        FROM "IT_jobs"."IT"
        WHERE
            title ILIKE $2
            OR required_skills ILIKE $2
        ORDER BY rank ASC, date_posted DESC
        LIMIT $3
    """

    exact_term = keyword.strip()
    fuzzy_term = f"%{keyword.strip()}%"
    try:
        async with _pool.acquire() as conn:
            records = await conn.fetch(query, exact_term, fuzzy_term, limit)
            return [
                {k: v for k, v in dict(record).items() if k != "rank"}
                for record in records
            ]
    except Exception as e:
        logger.error(f"Error fetching live jobs for '{keyword}': {e}")
        return []
