"""ESCO Occupation Matcher & Gap Analysis.

This module uses a lightweight LLM API call via OpenRouter to compute semantic similarity
between a user's skills and the required skills from the live ESCO API.
"""

from __future__ import annotations

import os
import json
import asyncio
import logging
from dataclasses import dataclass, asdict
from typing import Optional, List

import httpx

from app.services.cv_parser import ParsedCV
from app.services.esco_client import search_occupations, get_occupation_skills
from app.services.llm_utils import call_llm
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

@dataclass
class PathwayMatch:
    """Represents a matched career pathway and its gap analysis."""
    target_title: str
    category: str
    match_score_percent: int
    existing_skills: list[str]
    missing_skills: list[str]
    
    def to_dict(self) -> dict:
        return asdict(self)

async def match_occupations(parsed_cv: ParsedCV, top_k: int = 3) -> list[PathwayMatch]:
    """Match a parsed CV against ESCO occupations using an LLM as a semantic judge.
    
    Args:
        parsed_cv: The structured output from cv_parser.py
        top_k: Number of top pathways to return
        
    Returns:
        List of PathwayMatch objects sorted by highest skill overlap.
    """
    user_skills = [s.name for s in sorted(parsed_cv.skills, key=lambda x: x.weight, reverse=True) if s.weight > 0.2]
    
    if not user_skills:
        return []

    # 1. Search ESCO for candidate occupations
    candidate_occupations = await search_occupations(user_skills[:5], limit_per_keyword=3)
    if not candidate_occupations:
        return []
        
    candidate_uris = [occ["uri"] for occ in candidate_occupations]
    skills_tasks = [get_occupation_skills(uri) for uri in candidate_uris]
    skills_results = await asyncio.gather(*skills_tasks)

    # 2. Build prompt for LLM evaluation
    candidates_data = []
    for occ, req_skills in zip(candidate_occupations, skills_results):
        if not req_skills:
            continue
        candidates_data.append({
            "title": occ["title"],
            "required_skills": list(req_skills)
        })
        
    if not candidates_data:
        return []

    def _deterministic_fallback() -> list[PathwayMatch]:
        scored_matches = []
        for occ, req_skills in zip(candidate_occupations, skills_results):
            if not req_skills: continue
            req_skills_lower = {s.lower() for s in req_skills}
            user_skills_lower = {s.lower() for s in user_skills}
            existing = [s for s in req_skills if s.lower() in user_skills_lower]
            missing = [s for s in req_skills if s.lower() not in user_skills_lower]
            score = int((len(existing) / len(req_skills)) * 100) if req_skills else 0
            
            match = PathwayMatch(
                target_title=occ["title"],
                category="ESCO Match",
                match_score_percent=score,
                existing_skills=existing,
                missing_skills=missing
            )
            scored_matches.append(match)
        scored_matches.sort(key=lambda m: (m.match_score_percent, -len(m.missing_skills)), reverse=True)
        return scored_matches

    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Using deterministic fallback.")
        scored_matches = _deterministic_fallback()
    else:
        prompt = f"""
        You are an expert career and skills evaluator.

        USER SKILLS:
        {json.dumps(user_skills)}

        CANDIDATE OCCUPATIONS:
        {json.dumps(candidates_data, indent=2)}

        Task: Evaluate how well the USER SKILLS match the required skills for each candidate occupation.
        For each occupation, you must output:
        - target_title: The exact title of the candidate occupation.
        - match_score_percent: An integer between 0 and 100 representing how well the user skills cover the required skills based on semantic similarity and practical overlap. Be critical.
        - existing_skills: A list of required skills that the user already has (or has a very close semantic equivalent to). Limit to actual matches.
        - missing_skills: A list of required skills that the user clearly lacks.

        Return a JSON object with a single key "results" which is a list of these evaluation objects.
        """

        system_prompt = "You are a career evaluation assistant. Always return valid JSON."

        try:
            parsed_json = await call_llm(prompt, system_prompt, timeout=15.0) #timeout=45.0
            results = parsed_json.get("results", [])
            
            scored_matches = []
            for res in results:
                existing = res.get("existing_skills", [])
                missing = res.get("missing_skills", [])
                total = len(existing) + len(missing)
                # Override the model's freeform score with one that's actually
                # consistent with the existing/missing lists shown on the card.
                computed_score = int((len(existing) / total) * 100) if total else res.get("match_score_percent", 0)

                match = PathwayMatch(
                    target_title=res.get("target_title", ""),
                    category="ESCO Match",
                    match_score_percent=computed_score,
                    existing_skills=existing,
                    missing_skills=missing
                    # match_score_percent=res.get("match_score_percent", 0),
                    # existing_skills=res.get("existing_skills", []),
                    # missing_skills=res.get("missing_skills", [])
                )
                if match.target_title:
                    scored_matches.append(match)
                    
            scored_matches.sort(key=lambda m: (m.match_score_percent, -len(m.missing_skills)), reverse=True)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Error calling OpenRouter for matching: HTTP {e.response.status_code} - {e.response.text}. Using fallback.")
            scored_matches = _deterministic_fallback()
        except Exception as e:
            logger.error(f"Error calling OpenRouter for matching: {e}. Using fallback.")
            scored_matches = _deterministic_fallback()

    # Deduplicate
    unique_matches = []
    seen_titles = set()
    for m in scored_matches:
        if m.target_title.lower() not in seen_titles:
            seen_titles.add(m.target_title.lower())
            unique_matches.append(m)
            if len(unique_matches) == top_k:
                break
                
    return unique_matches
