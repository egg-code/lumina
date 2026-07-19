import os
import json
import httpx
from typing import List
from app.core.models import TitleMatch
from app.services.cv_parser import ParsedCV
from app.services.llm_utils import call_llm
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

async def enrich_matches(parsed_cv: ParsedCV, matches: List[TitleMatch]) -> List[TitleMatch]:
    if not OPENROUTER_API_KEY:
        print("Warning: OPENROUTER_API_KEY not set. Returning deterministic matches only.")
        return matches
    # Prepare data for LLM
    cv_summary = parsed_cv.summary()
    job_titles = [m.title for m in matches]
    
    if not job_titles:
        return matches

    live_jobs_context = []
    for m in matches:
        if hasattr(m, 'live_jobs') and m.live_jobs:
            jobs_str = ", ".join([f"'{j.title}' at {j.company}" for j in m.live_jobs])
            live_jobs_context.append(f"- For {m.title}, live openings: {jobs_str}")
        else:
            live_jobs_context.append(f"- For {m.title}, no immediate live openings found.")
    live_jobs_text = "\n".join(live_jobs_context)

    prompt = f"""
You are an expert career coach. Based on the user's CV summary, we have identified these top {len(matches)} matching career pathways:
{', '.join(job_titles)}

Live Job Openings in the market right now:
{live_jobs_text}

User CV Summary:
{cv_summary}

For each of these {len(matches)} job titles, provide the following structured analysis:
- why_fit: 1 short sentence on why their background fits this role (reference a live job if relevant).
- typical_timeframe: realistic onboarding time (e.g., '3-6 months', '1 year').
- actionable_steps: 3 concrete steps to bridge their skill gap (use the live job requirements if possible).
- target_profile: job title of someone they should do an informational interview with (e.g. Senior Product Manager).
- why_this_person: 1 short sentence on why this person is useful to talk to.
- search_keywords: 2-3 keywords to search for this person on LinkedIn (include 'Myanmar').
- informational_interview_questions: 2 good questions to ask this person.
- sprint: A list of exactly 7 short, daily tasks (strings) for a 1-week sprint to try out this role or build a portfolio piece.
- timeline: A list of exactly 3 items, where each item is a 2-element list: [phase_name, description] (e.g., [["0-3 months", "Build X"], ["3-6 months", "Learn Y"], ["6-12 months", "Apply to Z"]]).
- skills: A list of 4 key transferable skills needed for this role.
- examples: A list of 2 real-world anecdotes of people transitioning into this role.

Return a JSON object with a single key "results" which is a list of objects in the same order as the job titles. Each object must have the exact keys:
"why_fit", "typical_timeframe", "actionable_steps", "target_profile", "why_this_person", "search_keywords", "informational_interview_questions", "sprint", "timeline", "skills", "examples".
"""

    system_prompt = "You are a career mapping assistant. Always return valid JSON."

    try:
        parsed_json = await call_llm(prompt, system_prompt, timeout=45.0)
        results = parsed_json.get("results", [])
            
        # Enrich matches
        for i, match in enumerate(matches):
            if i < len(results):
                res = results[i]
                match.why_fit = res.get("why_fit", match.why_fit)
                match.typical_timeframe = res.get("typical_timeframe", match.typical_timeframe)
                match.actionable_steps = res.get("actionable_steps", match.actionable_steps)
                match.target_profile = res.get("target_profile", match.target_profile)
                match.why_this_person = res.get("why_this_person", match.why_this_person)
                match.search_keywords = res.get("search_keywords", match.search_keywords)
                match.informational_interview_questions = res.get("informational_interview_questions", match.informational_interview_questions)
                
                match.sprint = res.get("sprint", [])
                # timeline should be a list of tuples
                timeline_data = res.get("timeline", [])
                if isinstance(timeline_data, list):
                    match.timeline = [tuple(t) for t in timeline_data if isinstance(t, list) and len(t) == 2]
                match.skills = res.get("skills", [])
                match.examples = res.get("examples", [])
    except Exception as e:
        print(f"Error calling OpenRouter or parsing response: {e}")
        # Silently fallback to basic deterministic matches

    return matches
