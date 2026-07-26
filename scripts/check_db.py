"""
Database Inspection Script for Lumina

Run this script anytime to check total imported job count, country breakdowns,
portal breakdowns, and sample imported job records.
"""

import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def check_database():
    if not DATABASE_URL:
        print("Error: DATABASE_URL is not set in your .env file.")
        return

    print("Connecting to PostgreSQL Database...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        total_count = await conn.fetchval('SELECT COUNT(*) FROM "IT_jobs"."IT";')
        by_country = await conn.fetch('SELECT country, COUNT(*) FROM "IT_jobs"."IT" GROUP BY country ORDER BY COUNT(*) DESC;')
        by_source = await conn.fetch('SELECT source, COUNT(*) FROM "IT_jobs"."IT" GROUP BY source ORDER BY COUNT(*) DESC;')
        recent_jobs = await conn.fetch('SELECT title, company, country, source, job_link, required_skills, date_posted FROM "IT_jobs"."IT" ORDER BY date_posted DESC LIMIT 5;')

        print("\n" + "="*60)
        print(f"  LUMINA DATABASE STATUS REPORT")
        print("="*60)
        print(f"📊 Total Jobs in Database: {total_count:,}")

        print("\n📍 Breakdown by Country:")
        for r in by_country:
            country_name = "Thailand 🇹🇭" if r["country"] == "TH" else ("Malaysia 🇲🇾" if r["country"] == "MY" else r["country"])
            print(f"   - {country_name}: {r['count']:,} jobs")

        print("\n🌐 Breakdown by Portal Source:")
        for r in by_source:
            print(f"   - {r['source']}: {r['count']:,} jobs")

        print("\n💼 Sample Recently Posted Jobs:")
        for i, r in enumerate(recent_jobs, 1):
            print(f"\n   [{i}] {r['title']} @ {r['company'] or 'N/A'}")
            print(f"       Country: {r['country']} | Portal: {r['source']} | Date: {r['date_posted']}")
            print(f"       Direct Link: {r['job_link']}")
            print(f"       Extracted Skills: {r['required_skills'][:80] if r['required_skills'] else 'N/A'}...")

        print("\n" + "="*60)
        await conn.close()
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())
