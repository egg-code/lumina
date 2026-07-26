"""
ETL Ingestion Script for Lumina Live Jobs Data (lumina_ready.csv)

Parses 13,811 jobs from /home/eggcoder/code/jobs_etl/jobs_tracker_etl_v2/data/processed/lumina_ready.csv
Formats skills_json into searchable required_skills text, generates canonical job links,
creates PostgreSQL schema & trigram indexes, and batch-upserts records using asyncpg.
"""

import asyncio
import csv
import json
import os
import sys
import time
import logging
from pathlib import Path
import asyncpg
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

CSV_PATH = Path("/home/eggcoder/code/jobs_etl/jobs_tracker_etl_v2/data/processed/lumina_ready.csv")

def extract_skills_text(skills_json_raw: str) -> str:
    """Extract and deduplicate skills from skills_json string."""
    if not skills_json_raw:
        return ""
    try:
        data = json.loads(skills_json_raw)
        skills = []
        for category in ["technical_skills", "languages", "soft_skills"]:
            cat_data = data.get(category, {})
            if isinstance(cat_data, dict):
                skills.extend(cat_data.get("required", []))
                skills.extend(cat_data.get("nice_to_have", []))
        seen = set()
        unique_skills = [s.strip() for s in skills if s and s.strip() and not (s.strip().lower() in seen or seen.add(s.strip().lower()))]
        return ", ".join(unique_skills)
    except Exception:
        return ""

def generate_job_link(portal_source: str, job_id: str) -> str:
    """Generate canonical job listing URL based on portal source."""
    clean_id = str(job_id).strip()
    if "jobsdb" in portal_source.lower():
        return f"https://th.jobsdb.com/job/{clean_id}"
    elif "jobstreet" in portal_source.lower():
        return f"https://my.jobstreet.com/job/{clean_id}"
    return f"https://th.jobsdb.com/job/{clean_id}"

async def setup_schema(conn: asyncpg.Connection):
    """Ensure schema, table, extensions, and indexes exist."""
    logger.info("Setting up database schema and extensions...")
    
    # Enable pg_trgm extension for fast text matching if available
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        logger.info("pg_trgm extension enabled.")
    except Exception as e:
        logger.warning(f"Could not enable pg_trgm extension: {e}")

    await conn.execute("""
        CREATE SCHEMA IF NOT EXISTS "IT_jobs";
        
        CREATE TABLE IF NOT EXISTS "IT_jobs"."IT" (
            job_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT,
            location TEXT,
            country TEXT,
            work_arrangement TEXT,
            date_posted TEXT,
            job_link TEXT,
            source TEXT,
            required_skills TEXT,
            skills_json TEXT
        );
    """)

    # Ensure job_id has a UNIQUE or PRIMARY KEY constraint if created earlier without one
    try:
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conrelid = '"IT_jobs"."IT"'::regclass 
                    AND contype IN ('p', 'u')
                ) THEN
                    ALTER TABLE "IT_jobs"."IT" ADD CONSTRAINT it_jobs_pk PRIMARY KEY (job_id);
                END IF;
            END $$;
        """)
        logger.info("PRIMARY KEY constraint verified on job_id.")
    except Exception as e:
        logger.info(f"Primary key setup note: {e}")

    # Ensure all columns exist (in case table was created with old schema)
    columns_to_add = [
        ("country", "TEXT"),
        ("work_arrangement", "TEXT"),
        ("source", "TEXT"),
        ("required_skills", "TEXT"),
        ("skills_json", "TEXT"),
    ]
    for col_name, col_type in columns_to_add:
        try:
            await conn.execute(f'ALTER TABLE "IT_jobs"."IT" ADD COLUMN IF NOT EXISTS {col_name} {col_type};')
        except Exception as e:
            logger.warning(f"Note on adding column {col_name}: {e}")

    # Create indexes for high-speed search
    logger.info("Creating database search indexes...")
    try:
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_it_jobs_title_trgm ON "IT_jobs"."IT" USING gin (title gin_trgm_ops);')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_it_jobs_skills_trgm ON "IT_jobs"."IT" USING gin (required_skills gin_trgm_ops);')
    except Exception as e:
        logger.info(f"Fallback to standard B-tree index if pg_trgm is restricted: {e}")
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_it_jobs_title ON "IT_jobs"."IT" (title);')

    await conn.execute('CREATE INDEX IF NOT EXISTS idx_it_jobs_date_posted ON "IT_jobs"."IT" (date_posted DESC);')
    logger.info("Database schema setup complete.")

async def ingest_csv():
    if not DATABASE_URL:
        logger.error("DATABASE_URL is not set in environment or .env file.")
        sys.exit(1)

    if not CSV_PATH.exists():
        logger.error(f"CSV file not found at {CSV_PATH}")
        sys.exit(1)

    start_time = time.time()
    logger.info(f"Reading CSV file from {CSV_PATH}...")

    records = []
    with open(CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            portal_source = row.get("portal_source", "").strip()
            job_id_raw = row.get("job_id", "").strip()
            if not job_id_raw:
                continue

            # Prefix job_id to prevent collision across different portals
            prefixed_id = f"{portal_source}_{job_id_raw}" if portal_source else job_id_raw
            job_title = row.get("job_title", "").strip()
            company_name = row.get("company_name", "").strip()
            location = row.get("location", "").strip()
            country_code = row.get("country_code", "").strip()
            work_type = row.get("work_type", "").strip()
            posted_at_utc = row.get("posted_at_utc", "").strip()
            skills_json_raw = row.get("skills_json", "").strip()
            
            skills_text = extract_skills_text(skills_json_raw)
            job_link = generate_job_link(portal_source, job_id_raw)

            records.append((
                prefixed_id,
                job_title,
                company_name,
                location,
                country_code,
                work_type,
                posted_at_utc,
                job_link,
                portal_source,
                skills_text,
                skills_json_raw
            ))

    logger.info(f"Loaded {len(records)} records from CSV in {time.time() - start_time:.2f}s.")

    logger.info("Connecting to Neon PostgreSQL...")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        await setup_schema(conn)

        logger.info(f"Batch upserting {len(records)} records into \"IT_jobs\".\"IT\"...")
        upsert_query = """
            INSERT INTO "IT_jobs"."IT" (
                job_id, title, company, location, country,
                work_arrangement, date_posted, job_link,
                source, required_skills, skills_json
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            ON CONFLICT (job_id) DO UPDATE SET
                title = EXCLUDED.title,
                company = EXCLUDED.company,
                location = EXCLUDED.location,
                country = EXCLUDED.country,
                work_arrangement = EXCLUDED.work_arrangement,
                date_posted = EXCLUDED.date_posted,
                job_link = EXCLUDED.job_link,
                source = EXCLUDED.source,
                required_skills = EXCLUDED.required_skills,
                skills_json = EXCLUDED.skills_json;
        """

        batch_size = 1000
        total_inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            await conn.executemany(upsert_query, batch)
            total_inserted += len(batch)
            logger.info(f"Upserted {total_inserted}/{len(records)} records...")

        count = await conn.fetchval('SELECT COUNT(*) FROM "IT_jobs"."IT"')
        logger.info(f"Successfully finished ingestion! Total rows in database: {count}")
        logger.info(f"Total ETL execution time: {time.time() - start_time:.2f}s.")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(ingest_csv())
