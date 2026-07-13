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

async def fetch_live_jobs_for_title(keyword: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch live jobs matching a career title (e.g. "Data Analyst").

    Query strategy (dual-path for backwards compatibility):
      1. PRIMARY — exact match on `esco_title` column (set by ETL from v2 onwards).
         These are high-confidence matches: the job was tagged with the same ESCO
         standard title that Lumina assigned to the user's CV.
      2. FALLBACK — ILIKE fuzzy search on `title` and `required_skills` columns,
         used for rows inserted before the `esco_title` column was added.

    Both result sets are merged; exact ESCO matches are ranked first.
    """
    global _pool
    if _pool is None:
        await init_db_pool()

    if _pool is None:
        return []

    # Dual-path query:
    #   - Rows with a matching esco_title are returned first (ORDER BY rank)
    #   - Rows without esco_title fall back to ILIKE on title / required_skills
    query = """
        SELECT
            job_id, title, company, location,
            min_salary, max_salary, job_link, required_skills,
            CASE WHEN esco_title = $1 THEN 0 ELSE 1 END AS rank
        FROM "IT_jobs"."IT"
        WHERE
            esco_title = $1
            OR (
                esco_title IS NULL
                AND (title ILIKE $2 OR required_skills ILIKE $2)
            )
        ORDER BY rank ASC, date_posted DESC
        LIMIT $3
    """

    search_term = f"%{keyword}%"
    try:
        async with _pool.acquire() as conn:
            records = await conn.fetch(query, keyword, search_term, limit)
            # Strip the internal rank column before returning
            return [
                {k: v for k, v in dict(record).items() if k != "rank"}
                for record in records
            ]
    except Exception as e:
        logger.error(f"Error fetching live jobs for '{keyword}': {e}")
        return []
