"""Fetch a curated list of ESCO Occupations and their required skills.

This script fetches occupations across major domains (Tech, Business, etc.)
and then retrieves the 'essential' skills for each one to build our matching
profiles.

Output: data/occupations.json
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ESCO_API = "https://ec.europa.eu/esco/api"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "occupations.json"


def fetch_json(url):
    """GET a URL and return parsed JSON."""
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  Failed: {e}")
                return None


def search_occupations(query, limit=20):
    """Search for occupations matching the query."""
    params = urllib.parse.urlencode({
        "text": query,
        "type": "occupation",
        "language": "en",
        "limit": limit,
    })
    url = f"{ESCO_API}/search?{params}"
    data = fetch_json(url)
    if not data:
        return []
    
    results = data.get("_embedded", {}).get("results", [])
    return [{"uri": r["uri"], "title": r["title"]} for r in results]


def get_occupation_skills(uri):
    """Fetch essential skills for a specific occupation URI."""
    safe_uri = urllib.parse.quote(uri, safe="")
    url = f"{ESCO_API}/resource/occupation?uri={safe_uri}&language=en"
    data = fetch_json(url)
    if not data:
        return []
    
    # ESCO links essential skills via specific relation groups
    skills = []
    links = data.get("_links", {})
    
    # hasEssentialSkill
    essential = links.get("hasEssentialSkill", [])
    for skill in essential:
        skills.append({
            "uri": skill.get("uri"),
            "title": skill.get("title")
        })
        
    return skills


def main():
    # Curated list of search terms to pull common jobs for graduates
    search_terms = [
        # Tech & Data
        "software developer", "data analyst", "data scientist",
        "web developer", "systems analyst", "network engineer",
        "cyber security", "database administrator", "machine learning engineer",
        # Business & Finance
        "project manager", "business analyst", "accountant",
        "financial analyst", "marketing manager", "sales representative",
        "human resources", "supply chain manager",
        # Social & Governance
        "policy analyst", "public relations", "social worker",
        "research assistant", "program coordinator",
        # Engineering
        "civil engineer", "mechanical engineer", "electrical engineer"
    ]

    print(f"Fetching occupations for {len(search_terms)} domains...")
    
    occupations_map = {}
    
    for i, term in enumerate(search_terms):
        print(f"[{i+1}/{len(search_terms)}] Searching: {term}")
        occs = search_occupations(term, limit=3) # Get top 3 variants for each term
        
        for occ in occs:
            uri = occ["uri"]
            if uri in occupations_map:
                continue
                
            print(f"  -> Fetching skills for: {occ['title']}")
            skills = get_occupation_skills(uri)
            
            # Extract just the skill labels
            skill_labels = [s["title"] for s in skills]
            
            occupations_map[uri] = {
                "title": occ["title"],
                "essential_skills": skill_labels,
                "category": term
            }
            time.sleep(0.3)  # Polite API usage

    # Convert to list and save
    output = {
        "metadata": {
            "source": "ESCO API",
            "total_occupations": len(occupations_map)
        },
        "occupations": list(occupations_map.values())
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(occupations_map)} occupations to {OUTPUT}")


if __name__ == "__main__":
    main()
