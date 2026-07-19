"""LLM-powered Occupation Matcher & Gap Analysis.

Previously this module fetched candidate occupations from the live ESCO API
(ec.europa.eu/esco/api), fetched required skills per occupation, then made one
LLM call per occupation to evaluate fit. That chain added 30-60 s of external
HTTP latency and a fragile dependency on a third-party API.

Now a single LLM call does the whole job: given the parsed CV, it proposes the
top-k career paths and returns existing/missing skills for each — no external
HTTP calls needed.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict

from app.services.cv_parser import ParsedCV
from app.services.llm_utils import call_llm
from dotenv import load_dotenv
import os

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

# Max total "core skills" (existing + missing combined) shown for any one
# occupation. Keeps the job-matches card readable — and, just as importantly,
# this is the same cap the skill-gap page enforces on the exact same list so
# both pages report the same total for a given role.
MAX_CORE_SKILLS = 15

def _cap_core_skills(existing: list[str], missing: list[str], max_total: int = MAX_CORE_SKILLS) -> tuple[list[str], list[str]]:
    """Cap existing+missing to at most max_total skills, keeping the user's
    matched (existing) skills first since those are the proof of fit, and
    trimming the \"to build\" list to fit the remaining budget."""
    if len(existing) + len(missing) <= max_total:
        return existing, missing
    existing = existing[:max_total]
    remaining = max(max_total - len(existing), 0)
    return existing, missing[:remaining]


async def match_occupations(parsed_cv: ParsedCV, top_k: int = 3) -> list[PathwayMatch]:
    """Match a parsed CV against career pathways using a single LLM call.

    The LLM is asked to propose the top-k most suitable career paths given
    the candidate's skills and experience, and to break down existing vs
    missing skills for each path. No external API calls are made.

    Args:
        parsed_cv: The structured output from cv_parser.py
        top_k: Number of top pathways to return

    Returns:
        List of PathwayMatch objects sorted by highest skill overlap.
    """
    user_skills = [
        s.name
        for s in sorted(parsed_cv.skills, key=lambda x: x.weight, reverse=True)
        if s.weight > 0.2
    ]

    if not user_skills:
        logger.warning("No skills found in CV — cannot match occupations.")
        return []

    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — cannot match occupations.")
        return []

    # Build a compact CV summary for the prompt
    experience_lines = (
        ", ".join(f"{e.title} ({e.duration})" for e in parsed_cv.experience[:5])
        if parsed_cv.experience
        else "Not specified"
    )
    domain = parsed_cv.profile.domain or "Not specified"
    seniority = parsed_cv.profile.seniority or "Not specified"
    years_exp = parsed_cv.profile.years_of_experience or "Unknown"

    prompt = f"""
You are an expert career coach with deep knowledge of global job markets.

CANDIDATE PROFILE:
- Seniority: {seniority}
- Domain: {domain}
- Years of experience: {years_exp}
- Recent roles: {experience_lines}

CANDIDATE SKILLS (ordered by relevance):
{json.dumps(user_skills)}

TASK: Identify the {top_k} most suitable career paths for this candidate based
on their actual skills and experience — the way an experienced recruiter would
assess fit today.

For each career path:
- "title": a specific, real-world job title (e.g. "Data Analyst", not "Data Person")
- "category": the broad field (e.g. "Data Science", "Software Engineering", "Product Management")
- "existing_skills": skills from the candidate's profile that are directly relevant
  to this role. Use the actual skill names from the candidate's list above, or very
  close synonyms. Be generous with reasonable matches.
- "missing_skills": the most critical skills this role requires that the candidate
  clearly lacks. Keep this list focused — only genuinely important gaps.
- existing_skills + missing_skills combined must NOT exceed {MAX_CORE_SKILLS} items total.

Return a JSON object with exactly this schema:
{{
  "matches": [
    {{
      "title": "...",
      "category": "...",
      "existing_skills": ["skill1", "skill2"],
      "missing_skills": ["skill3", "skill4"]
    }}
  ]
}}

Return exactly {top_k} matches, ordered from best fit to least fit.
Do not add any keys beyond the ones shown. Do not omit any keys shown.
"""
    system_prompt = "You are a career evaluation assistant. Always return valid JSON."

    try:
        parsed_json = await call_llm(prompt, system_prompt, timeout=30.0, max_tokens=2000)
        matches_data = parsed_json.get("matches", [])

        results = []
        for m in matches_data[:top_k]:
            existing = m.get("existing_skills", [])
            missing = m.get("missing_skills", [])
            existing, missing = _cap_core_skills(existing, missing)
            total = len(existing) + len(missing)
            score = int((len(existing) / total) * 100) if total else 0
            results.append(PathwayMatch(
                target_title=m.get("title", "Unknown"),
                category=m.get("category", "General"),
                match_score_percent=score,
                existing_skills=existing,
                missing_skills=missing,
            ))

        logger.info("match_occupations: returned %d matches via LLM.", len(results))
        return results

    except Exception as e:
        logger.error("LLM match_occupations failed: %s — returning empty list.", e)
        return []
