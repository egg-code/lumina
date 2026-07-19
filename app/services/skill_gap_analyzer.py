import os
import json
import asyncio
import logging
import hashlib
from typing import Dict, Tuple

import time
import httpx
from dotenv import load_dotenv

from app.core.models import SkillGapResponse

load_dotenv()
logger = logging.getLogger(__name__)

from app.services.llm_utils import call_llm
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Simple in-memory LRU cache
_cache: Dict[str, Tuple[float, SkillGapResponse]] = {}  # key -> (timestamp, response)
CACHE_TTL_SECONDS = 3600  # 1 hour

def _cache_key(cv_text: str, target_title: str) -> str:
    return hashlib.sha256(f"{cv_text}:{target_title}".encode()).hexdigest()[:16]

def _reconcile_to_core_list(
    core_skills: list[str],
    overlapping: list[str],
    missing_detail: list[dict],
) -> tuple[list[str], list[dict]]:
    """Force the LLM's classification to cover exactly `core_skills` — the
    same capped core-skills list the job-matches card already computed
    (job_title_matcher._evaluate_occupation) — so both pages always report
    the same total for a given role instead of drifting apart.

    Drops anything the model hallucinated outside the list, and fills in
    any core skill the model forgot to classify (defaulting it to missing,
    marked "nice_to_have" so it doesn't overstate severity)."""
    core_set = set(core_skills)
    overlapping = [s for s in overlapping if s in core_set]
    missing_detail = [m for m in missing_detail if m.get("name") in core_set]

    classified = set(overlapping) | {m.get("name") for m in missing_detail}
    for skill in core_skills:
        if skill not in classified:
            missing_detail.append({
                "name": skill,
                "severity": "nice_to_have",
                "category": "domain",
                "user_has_equivalent": False,
                "equivalent_skill": ""
            })
    return overlapping, missing_detail

def _build_esco_only_fallback(existing_skills: list[str], missing_skills: list[str], target_title: str) -> SkillGapResponse:
    # Just basic matching logic if LLM fails
    score = 0
    total = len(existing_skills) + len(missing_skills)
    if total > 0:
        score = int((len(existing_skills) / total) * 100)
    
    return SkillGapResponse(
        target_title=target_title,
        match_score_percent=score,
        readiness_label="Unknown",
        total_learning_hours_estimate=0,
        overlapping_skills=existing_skills,
        missing_skills_detail=[
            {
                "name": s,
                "severity": "critical",
                "category": "technical",
                "user_has_equivalent": False,
                "equivalent_skill": ""
            } for s in missing_skills
        ],
        excess_skills=[],
        experience_gaps=[],
        recommendations=[],
        enriched_by_llm=False
    )

async def analyze_skill_gap(
    cv_text: str,
    target_title: str,
    existing_skills: list[str],
    missing_skills: list[str],
) -> SkillGapResponse:
    # Check cache
    cache_key = _cache_key(cv_text, target_title)
    import time
    now = time.time()
    if cache_key in _cache:
        ts, cached_res = _cache[cache_key]
        if now - ts < CACHE_TTL_SECONDS:
            return cached_res

    # If we were handed a pre-computed core-skills list (from the job-matches
    # card via job_title_matcher._evaluate_occupation), that list is the
    # single source of truth for "what skills matter for this role" — both
    # pages must count against the exact same list, or their totals drift
    # apart (this is what caused "17 of 36" vs "7 of 13"). For a custom
    # role typed by the user, existing/missing will be empty and we fall
    # back to letting the LLM curate its own list from scratch.
    combined_core_skills = list(dict.fromkeys(existing_skills + missing_skills))
    has_fixed_core_list = len(combined_core_skills) > 0

    # Prepare prompts
    system_a = "You are an expert career coach and skills assessor with deep knowledge of job markets. Always return valid JSON."

    if has_fixed_core_list:
        core_skills_instructions = f"""
IMPORTANT — FIXED CORE SKILLS LIST:
The {len(combined_core_skills)} skills below are the exact, already-filtered
"core skills" list for this role (computed upstream, capped to the most
essential skills). You MUST use this exact list for overlapping_skills and
missing_skills_detail — do not add any skill that is not in it, and do not
drop any skill from it. Your only job for those two fields is to classify
each of these skills as either overlapping (the user has it or a close
equivalent) or missing (the user lacks it), based on the CV below.

CORE SKILLS TO CLASSIFY (must appear, collectively, in overlapping_skills +
missing_skills_detail — nothing added, nothing omitted):
{json.dumps(combined_core_skills)}
"""
    else:
        core_skills_instructions = """
No pre-computed core skills list was provided (custom role) — determine the
most relevant skills for this role yourself.
"""

    prompt_a = f"""
USER CV:
{cv_text}

TARGET ROLE: {target_title}
{core_skills_instructions}
TASK: Perform a thorough skills and experience gap analysis.

Instructions:
1. For missing_skills_detail: {"Classify only the fixed core skills list above — see FIXED CORE SKILLS LIST instructions." if has_fixed_core_list else "Include ALL skills this role typically requires that the user doesn't clearly have — add domain knowledge, tools, soft skills that are actually needed."}
2. For excess_skills: List user's skills NOT typically needed for {target_title}.
3. For experience_gaps: Select the 3-5 MOST RELEVANT experience differences
   between what the user has done and what this role actually requires day-to-day.
   Focus on impact, not just titles.
4. For readiness_label: Be honest and realistic, not overly optimistic. (e.g. "Ready Now", "3-6 months", "6-12 months", "1+ year")
5. For total_learning_hours_estimate: Sum of hours to become job-ready across
   all critical missing skills.
6. Make sure overlapping_skills contains skills the user HAS that are relevant to this role.

Return JSON with this exact schema:
{{
  "match_score_percent": <0-100 integer>,
  "readiness_label": "Ready Now" | "3-6 months" | "6-12 months" | "1+ year",
  "total_learning_hours_estimate": <integer>,
  "overlapping_skills": ["skill1", "skill2"],
  "missing_skills_detail": [
    {{
      "name": "...",
      "severity": "critical" | "nice_to_have",
      "category": "technical" | "soft" | "domain" | "tool",
      "user_has_equivalent": true,
      "equivalent_skill": "..."
    }}
  ],
  "excess_skills": ["..."],
  "experience_gaps": [
    {{
      "area": "...",
      "user_has": "...",
      "role_needs": "...",
      "bridge_note": "...",
      "relevance_score": 10
    }}
  ]
}}


STRICT FIELD RULES (violating any of these will break the app — follow exactly):
- Every object in missing_skills_detail MUST include all five keys: "name",
  "severity", "category", "user_has_equivalent", "equivalent_skill". Never
  omit "user_has_equivalent" — if there is no equivalent, set it to false
  and leave "equivalent_skill" as an empty string "".
- "severity" must be exactly "critical" or "nice_to_have" — no other values.
- "category" must be exactly one of "technical", "soft", "domain", "tool".
- "user_has_equivalent" must be a JSON boolean (true or false), never a
  string like "true" or "yes".
- Every object in experience_gaps MUST include all five keys: "area",
  "user_has", "role_needs", "bridge_note", "relevance_score".
- "relevance_score" must be a JSON integer from 1 to 10, never a string
  or a word like "high".
- "match_score_percent" and "total_learning_hours_estimate" must be JSON
  integers, never strings or floats.
- "readiness_label" must be exactly one of: "Ready Now", "3-6 months",
  "6-12 months", "1+ year" — no other wording or extra punctuation.
- Do not add any keys beyond the ones listed in the schema above.
- Do not omit any key shown in the schema above, even if the list for
  that section would otherwise be empty — return an empty array [] instead
  of leaving the key out.
"""

    system_b = "You are a learning pathway expert. Recommend specific, real learning resources. Always return valid JSON."
    prompt_b = f"""
TARGET ROLE: {target_title}
SKILLS TO LEARN (priority order — critical first):
{json.dumps(missing_skills) if missing_skills else "Identify the 3-5 most critical skills needed for this role and provide resources for them."}

For each skill, provide 2-3 learning resources. Rules:
- Prioritize FREE resources (Coursera free audit, freeCodeCamp, YouTube, official docs, Google certificates, Kaggle Learn, MDN Web Docs)
- Provide REAL, specific URLs
- The url field should be the actual course URL (best-effort, may change over time)
- Order resources: Free before Paid
- Match difficulty to a career-switcher, not a complete beginner

Return JSON with this exact schema:
{{
  "recommendations": [
    {{
      "skill_name": "...",
      "priority": 1,
      "reason": "1-sentence reason why this is important",
      "resources": [
        {{
          "title": "...",
          "provider": "...",
          "url": "...",
          "duration_hours": 10,
          "cost": "Free",
          "format": "video",
          "difficulty": "beginner"
        }}
      ]
    }}
  ]
}}
"""

    if not OPENROUTER_API_KEY:
        return _build_esco_only_fallback(existing_skills, missing_skills, target_title)

    print(f"[SKILL GAP] analyzing '{target_title}' — starting gap_task + course_task in parallel...")
    t_start = time.time()

    # timeout=15.0 — was uncapped (defaulted to call_llm's 60.0s), so with
    # parallel calls it could take ~2 minutes. 30s is more reasonable.
    gap_task = asyncio.create_task(call_llm(prompt_a, system_a, timeout=30.0))
    course_task = asyncio.create_task(call_llm(prompt_b, system_b, timeout=30.0))

    #gap_task = asyncio.create_task(call_llm(prompt_a, system_a))
    #course_task = asyncio.create_task(call_llm(prompt_b, system_b))

    gap_result, course_result = await asyncio.gather(
        gap_task, course_task,
        return_exceptions=True
    )
    print(f"[SKILL GAP] both tasks settled after {time.time() - t_start:.1f}s")


    if isinstance(gap_result, Exception):
        logger.error(f"Gap analysis failed: {gap_result}")
        return _build_esco_only_fallback(existing_skills, missing_skills, target_title)
        
    recommendations = []
    if not isinstance(course_result, Exception):
        recommendations = course_result.get("recommendations", [])
    else:
        logger.warning(f"Course recommendation failed: {course_result}")
        
    try:
      overlapping_skills = gap_result.get("overlapping_skills", existing_skills)
      missing_skills_detail = gap_result.get("missing_skills_detail", [])
      match_score = gap_result.get("match_score_percent", 0)

      if has_fixed_core_list:
          overlapping_skills, missing_skills_detail = _reconcile_to_core_list(
              combined_core_skills, overlapping_skills, missing_skills_detail
          )
          # Recompute the score off the reconciled counts so it's always
          # consistent with what's actually shown — same pattern used in
          # job_title_matcher._evaluate_occupation.
          match_score = int((len(overlapping_skills) / len(combined_core_skills)) * 100)

      response = SkillGapResponse(
          target_title=target_title,
          match_score_percent=match_score,
          readiness_label=gap_result.get("readiness_label", "Unknown"),
          total_learning_hours_estimate=gap_result.get("total_learning_hours_estimate", 0),
          overlapping_skills=overlapping_skills,
          missing_skills_detail=missing_skills_detail,
          excess_skills=gap_result.get("excess_skills", []),
          experience_gaps=gap_result.get("experience_gaps", []),
          recommendations=recommendations,
          enriched_by_llm=True
      )
    except Exception as e:
        # The LLM returned valid JSON but it didn't match SkillGapResponse's
        # schema exactly. Print the raw payload so you can see exactly which
        # field broke, then fall back instead of 502-ing the request.
        print(f"\n[SKILL GAP] Pydantic validation failed for '{target_title}': {e}")
        print(f"[SKILL GAP] raw gap_result: {json.dumps(gap_result, indent=2)}")
        logger.error(f"SkillGapResponse validation failed for '{target_title}': {e}")
        return _build_esco_only_fallback(existing_skills, missing_skills, target_title)

    
    _cache[cache_key] = (now, response)
    return response
