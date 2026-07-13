"""Fetch ESCO skills taxonomy and save as a local JSON file.

Uses the ESCO REST API search endpoint (fast, no auth required).
Skips per-item detail calls — search results already contain labels.

To get broader coverage, we search for multiple common skill-related terms
rather than relying on the scheme filter (which caps at ~200 results).

Output: data/skills_taxonomy.json
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ESCO_API = "https://ec.europa.eu/esco/api"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"


def fetch_json(url):
    """GET a URL and return parsed JSON. Retries once on failure."""
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == 0:
                print(f"  Retry after error: {e}")
                time.sleep(2)
            else:
                raise


def search_esco(query, result_type="skill", limit=100):
    """Search ESCO for skills/knowledge matching a query string."""
    all_results = []
    offset = 0
    while True:
        params = urllib.parse.urlencode({
            "text": query,
            "type": result_type,
            "language": "en",
            "offset": offset,
            "limit": limit,
        })
        url = f"{ESCO_API}/search?{params}"
        data = fetch_json(url)
        results = data.get("_embedded", {}).get("results", [])
        if not results:
            break
        for item in results:
            all_results.append({
                "uri": item.get("uri", ""),
                "label": item.get("title", ""),
            })
        total = data.get("total", 0)
        offset += limit
        if offset >= total:
            break
        time.sleep(0.2)
    return all_results


def main():
    # Strategy: search for many broad terms to collect a wide set of skills.
    # The ESCO search endpoint returns up to ~200 per query, so we use
    # many targeted queries across different domains to get broad coverage.
    search_terms = [
        # Tech / IT
        "programming", "software", "database", "web development",
        "data analysis", "machine learning", "cloud computing",
        "cybersecurity", "networking", "system administration",
        "mobile development", "DevOps", "API", "testing",
        "artificial intelligence", "data science", "blockchain",
        "user interface", "user experience",
        # Business / Management
        "project management", "business analysis", "marketing",
        "financial analysis", "accounting", "human resources",
        "supply chain", "operations management", "strategic planning",
        "sales", "customer service", "business development",
        "risk management", "quality management",
        # Communication / Soft skills
        "communication", "leadership", "teamwork", "negotiation",
        "presentation", "writing", "problem solving", "critical thinking",
        "time management", "decision making", "conflict resolution",
        "coaching", "mentoring", "facilitation",
        # Research / Academic
        "research", "statistical analysis", "qualitative research",
        "survey", "data collection", "scientific writing",
        "literature review", "methodology",
        # Social Science / Governance
        "policy analysis", "monitoring and evaluation",
        "stakeholder engagement", "governance", "public administration",
        "international relations", "development", "humanitarian",
        "advocacy", "fundraising", "grant writing",
        # Design / Creative
        "graphic design", "visual design", "content creation",
        "photography", "video production", "branding",
        # Health
        "public health", "health education", "clinical",
        "patient care", "health management",
        # Languages / Translation
        "translation", "interpretation", "language teaching",
        # Engineering
        "electrical engineering", "mechanical engineering",
        "civil engineering", "environmental engineering",
        # General tools
        "spreadsheet", "office", "digital literacy",
        "social media", "content management",
    ]

    print(f"Searching ESCO for {len(search_terms)} skill domains...")

    # Deduplicate by URI
    all_skills = {}
    for i, term in enumerate(search_terms):
        print(f"  [{i+1}/{len(search_terms)}] Searching: '{term}'")
        try:
            results = search_esco(term, "skill")
            new_count = 0
            for skill in results:
                if skill["uri"] not in all_skills:
                    all_skills[skill["uri"]] = skill
                    new_count += 1
            if new_count > 0:
                print(f"    Found {len(results)} results, {new_count} new")
        except Exception as e:
            print(f"    ⚠ Failed: {e}")
        time.sleep(0.3)

    skills_list = list(all_skills.values())
    print(f"\nTotal unique skills collected: {len(skills_list)}")

    # Build flat lookup set (lowercase labels for fast matching)
    lookup_labels = sorted({s["label"].lower() for s in skills_list})

    # Categorize into rough groups based on URI patterns
    # ESCO URIs contain the concept scheme info
    skills_entries = []
    knowledge_entries = []

    for s in skills_list:
        entry = {"uri": s["uri"], "label": s["label"], "alt_labels": []}
        # ESCO knowledge concepts have a specific URI pattern
        if "/knowledge/" in s["uri"]:
            knowledge_entries.append(entry)
        else:
            skills_entries.append(entry)

    output = {
        "version": "esco_v1.2_search",
        "skills": skills_entries,
        "knowledge": knowledge_entries,
        "lookup_labels": lookup_labels,
        "stats": {
            "total_skills": len(skills_entries),
            "total_knowledge": len(knowledge_entries),
            "total_unique_labels": len(lookup_labels),
        },
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved to {OUTPUT}")
    print(f"   Skills: {output['stats']['total_skills']}")
    print(f"   Knowledge: {output['stats']['total_knowledge']}")
    print(f"   Total unique labels: {output['stats']['total_unique_labels']}")
    print(f"\nSample labels:")
    for label in lookup_labels[:20]:
        print(f"   {label}")


if __name__ == "__main__":
    main()
