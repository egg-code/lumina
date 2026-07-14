"""ESCO Occupation Matcher & Gap Analysis.

This module uses a lightweight LLM API call via OpenRouter to compute semantic similarity
between a user's skills and the required skills from the live ESCO API.
"""

from __future__ import annotations

import os
import re
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

# ---------------------------------------------------------------------------
# Word/token-overlap matching — used as a fallback when the LLM call for a
# given occupation fails. Replaces the old exact-string-equality check, which
# almost never matched because ESCO's skill phrasing ("manage project
# resources") rarely equals a user's short skill label ("Project Management").
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "and", "or", "the", "a", "an", "of", "to", "in", "for", "with", "on",
    "at", "by", "is", "are", "as", "be", "using", "use", "via",
}

def _tokenize_skill(skill: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", skill.lower())
    return {w for w in words if len(w) > 2 and w not in _STOPWORDS}

def _skills_overlap(required_skill: str, user_skill: str) -> bool:
    """True if the two skill phrases share enough meaningful words to be
    considered the same skill (a forgiving stand-in for semantic matching)."""
    req_tokens = _tokenize_skill(required_skill)
    user_tokens = _tokenize_skill(user_skill)
    if not req_tokens or not user_tokens:
        return False
    shared = req_tokens & user_tokens
    if not shared:
        return False
    overlap_ratio = len(shared) / min(len(req_tokens), len(user_tokens))
    return overlap_ratio >= 0.5

def _word_overlap_match(req_skills: list[str], user_skills: list[str]) -> tuple[list[str], list[str]]:
    """Split required_skills into (existing, missing) using word-overlap
    scoring against the user's skills, instead of exact string equality."""
    existing, missing = [], []
    for req in req_skills:
        if any(_skills_overlap(req, us) for us in user_skills):
            existing.append(req)
        else:
            missing.append(req)
    return existing, missing

# ---------------------------------------------------------------------------
# Per-occupation evaluation — mirrors skill_gap_analyzer.analyze_skill_gap():
# one focused LLM call per item (small prompt/response, low truncation risk),
# run concurrently via asyncio.gather, with a graceful per-item fallback.
# ---------------------------------------------------------------------------

async def _evaluate_occupation(title: str, req_skills: list[str], user_skills: list[str]) -> PathwayMatch:
    fallback_existing, fallback_missing = _word_overlap_match(req_skills, user_skills)
    fallback_score = int((len(fallback_existing) / len(req_skills)) * 100) if req_skills else 0

    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set. Using word-overlap fallback for '%s'.", title)
        return PathwayMatch(
            target_title=title,
            category="ESCO Match",
            match_score_percent=fallback_score,
            existing_skills=fallback_existing,
            missing_skills=fallback_missing
        )

    prompt = f"""
    You are an expert career and skills evaluator.

    USER SKILLS:
    {json.dumps(user_skills)}

    TARGET OCCUPATION: {title}
    REQUIRED SKILLS FOR THIS OCCUPATION:
    {json.dumps(req_skills)}

    Task: Evaluate how well the USER SKILLS match the required skills for this occupation.
    Output:
    - existing_skills: required skills (copied exactly as given) that the user already has, or
      has a very close semantic equivalent to. Be generous with reasonable synonyms and phrasing
      differences (e.g. "Project Management" counts as a match for "manage project resources").
    - missing_skills: required skills (copied exactly as given) that the user clearly lacks.

    Return a JSON object with exactly two keys: "existing_skills" and "missing_skills".
    """
    system_prompt = "You are a career evaluation assistant. Always return valid JSON."

    try:
        parsed_json = await call_llm(prompt, system_prompt, timeout=15.0, max_tokens=1200)
        existing = parsed_json.get("existing_skills", [])
        missing = parsed_json.get("missing_skills", [])
        total = len(existing) + len(missing)
        score = int((len(existing) / total) * 100) if total else fallback_score
        return PathwayMatch(
            target_title=title,
            category="ESCO Match",
            match_score_percent=score,
            existing_skills=existing,
            missing_skills=missing
        )
    except httpx.HTTPStatusError as e:
        logger.error(
            "Error calling OpenRouter for '%s': HTTP %s - %s. Using word-overlap fallback.",
            title, e.response.status_code, e.response.text
        )
    except Exception as e:
        logger.error("Error calling OpenRouter for '%s': %s. Using word-overlap fallback.", title, e)

    return PathwayMatch(
        target_title=title,
        category="ESCO Match",
        match_score_percent=fallback_score,
        existing_skills=fallback_existing,
        missing_skills=fallback_missing
    )

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

    # 2. Evaluate each candidate occupation concurrently, one focused LLM
    #    call per occupation (same pattern as skill_gap_analyzer.py's
    #    gap_task/course_task gather) instead of one large multi-occupation
    #    prompt that risked truncating past max_tokens.
    eval_tasks = []
    titles_for_tasks = []
    for occ, req_skills in zip(candidate_occupations, skills_results):
        if not req_skills:
            continue
        eval_tasks.append(_evaluate_occupation(occ["title"], list(req_skills), user_skills))
        titles_for_tasks.append(occ["title"])

    if not eval_tasks:
        return []

    results = await asyncio.gather(*eval_tasks, return_exceptions=True)

    scored_matches = []
    for title, res in zip(titles_for_tasks, results):
        if isinstance(res, Exception):
            logger.error("Occupation evaluation raised unexpectedly for '%s': %s", title, res)
            continue
        scored_matches.append(res)

    scored_matches.sort(key=lambda m: (m.match_score_percent, -len(m.missing_skills)), reverse=True)

    # 3. Deduplicate
    unique_matches = []
    seen_titles = set()
    for m in scored_matches:
        if m.target_title.lower() not in seen_titles:
            seen_titles.add(m.target_title.lower())
            unique_matches.append(m)
            if len(unique_matches) == top_k:
                break

    return unique_matches
