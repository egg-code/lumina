import asyncio
import httpx
from typing import List, Dict, Any, Set
import logging

logger = logging.getLogger(__name__)

ESCO_BASE_URL = "https://ec.europa.eu/esco/api"

async def search_occupations(skill_keywords: List[str], limit_per_keyword: int = 5) -> List[Dict[str, Any]]:
    """
    Search ESCO occupations by a list of skill keywords.
    Returns a deduplicated list of occupation dictionaries (containing 'uri' and 'title').
    """
    results = []
    seen_uris = set()
    
    async with httpx.AsyncClient() as client:
        # We process keywords concurrently to speed up the search
        async def fetch_for_keyword(kw: str):
            try:
                response = await client.get(
                    f"{ESCO_BASE_URL}/search",
                    params={"text": kw, "type": "occupation", "limit": limit_per_keyword},
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return data.get("_embedded", {}).get("results", [])
            except Exception as e:
                logger.error(f"ESCO API search error for '{kw}': {e}")
                return []
                
        tasks = [fetch_for_keyword(kw) for kw in skill_keywords[:5]] # Limit to top 5 skills to avoid too many requests
        kw_results = await asyncio.gather(*tasks)
        
        for kw_result in kw_results:
            for item in kw_result:
                uri = item.get("uri")
                if uri and uri not in seen_uris:
                    seen_uris.add(uri)
                    results.append({
                        "uri": uri,
                        "title": item.get("title", "Unknown")
                    })
                    
    return results

async def get_occupation_skills(uri: str) -> Set[str]:
    """
    Fetch the essential and optional skills for a given occupation URI.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{ESCO_BASE_URL}/resource/occupation",
                params={"uri": uri},
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            skills = set()
            
            # ESCO API returns skills usually in _links.hasEssentialSkill or _links.hasOptionalSkill
            links = data.get("_links", {})
            
            essential_skills = links.get("hasEssentialSkill", [])
            for skill in essential_skills:
                title = skill.get("title")
                if title:
                    skills.add(title.lower())
                    
            optional_skills = links.get("hasOptionalSkill", [])
            for skill in optional_skills:
                title = skill.get("title")
                if title:
                    skills.add(title.lower())
                    
            return skills
        except Exception as e:
            logger.error(f"ESCO API resource error for '{uri}': {e}")
            return set()
