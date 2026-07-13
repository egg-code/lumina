"""FastAPI app: serves the static frontend and the two API routes,
POST /api/match-titles and POST /api/sprint. See engineering.md Section 7
(API surface) — updated for v0.4 (action_steps.md #10).

v0.3 removed POST /api/classify and the closed 5-category set it scored
CVs against, replacing it with one open-corpus TF-IDF match step plus a
live Claude call per matched title to generate sprint content.

v0.4 removes that live call too. There is now no LLM, no network call,
and no `ANTHROPIC_API_KEY` anywhere in this backend — both routes are
pure, free, deterministic TF-IDF lookups (`app/job_title_matcher.py` for
title matching, `app/sprint_matcher.py` for sprint-content assignment).
This was a deliberate trade — see action_steps.md #10 for the user's
stated reason (no budget for metered API costs on an educational
project) and what's given up to get to $0/request.

Note: this module only *defines* the app. Nothing in this codebase starts
a dev server — running `uvicorn app.main:app` live is a deliberate,
separate, later step, per this build's instructions.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
import io
import asyncio

from app.services.job_title_matcher import match_occupations
from app.services.cv_parser import parse_cv
from app.core.models import (
    MatchTitlesRequest,
    MatchTitlesResponse,
    TitleMatch,
    LiveJob,
    SkillGapRequest,
    SkillGapResponse
)
from app.services.llm_client import enrich_matches
from app.db.database import fetch_live_jobs_for_title
from app.services.skill_gap_analyzer import analyze_skill_gap

# Updated robust static directory resolution
STATIC_DIR = Path("static").resolve()
if not STATIC_DIR.exists():
    STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

# Cited on every /api/match-titles response.
JOB_TITLE_CORPUS_SOURCE = (
    "ESCO Occupations Database (European Skills, Competences, "
    "Qualifications and Occupations). Used for transparent, deterministic "
    "skill gap analysis."
)

app = FastAPI(title="ProofPath", version="0.4.0")


@app.post("/api/match-titles", response_model=MatchTitlesResponse)
async def match_titles_endpoint(request: MatchTitlesRequest) -> MatchTitlesResponse:
    """The product's one "find my title" step (action_steps.md #7-#9):
    ranks the CV's own text — pure TF-IDF + cosine similarity, no network
    call — against the full ~1,000-title open corpus, descending by score.

    Then, it uses OpenRouter LLM to dynamically enrich the matches with gap analysis, 
    actionable steps, and networking strategies.
    """
    try:
        parsed_cv = await parse_cv(request.cv_text)
        results = await match_occupations(parsed_cv, top_k=request.top_n)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Couldn't run the title search. Try again in a moment.",
        ) from exc

    # matches = []
    # for match in results:
    #     live_job_dicts = await fetch_live_jobs_for_title(match.target_title)
    #     live_jobs_objects = [LiveJob(**lj) for lj in live_job_dicts]
    #     matches.append(
    #         TitleMatch(
    #             title=match.target_title,
    #             category=match.category,
    #             match_score_percent=match.match_score_percent,
    #             existing_skills=match.existing_skills,
    #             missing_skills=match.missing_skills,
    #             live_jobs=live_jobs_objects
    #         )
    #     )

    live_job_lists = await asyncio.gather(
        *[fetch_live_jobs_for_title(match.target_title) for match in results]
    )
    matches = []
    for match, live_job_dicts in zip(results, live_job_lists):
        live_jobs_objects = [LiveJob(**lj) for lj in live_job_dicts]
        matches.append(TitleMatch(
            title=match.target_title,
            category=match.category,
            match_score_percent=match.match_score_percent,
            existing_skills=match.existing_skills,
            missing_skills=match.missing_skills,
            live_jobs=live_jobs_objects
        ))
    
    # Enrich with OpenRouter LLM
    matches = await enrich_matches(parsed_cv, matches)

    return MatchTitlesResponse(
        matches=matches,
        corpus_size=1000, # Will be replaced once ESCO client counts dynamically, assuming ~1000 for now. Or we can just use 0. Let's use 0.
        source=JOB_TITLE_CORPUS_SOURCE,
    )

@app.post("/api/extract-text")
async def extract_file_text(file: UploadFile = File(...)):
    """Extract raw text from uploaded PDF, DOCX, or TXT files."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    filename = file.filename.lower()
    content = await file.read()
    
    try:
        if filename.endswith(".pdf"):
            import pypdf
            import re
            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            
            # Fix spaced out characters from certain PDFs (e.g. 'P o s t g r e S Q L')
            single_char_words = len(re.findall(r'(?<!\S)\S(?!\S)', text))
            total_words = len(text.split())
            if total_words > 0 and (single_char_words / total_words) > 0.4:
                text = text.replace('  ', '<SPACE>')
                text = re.sub(r'(?<=\S) (?=\S)', '', text)
                text = text.replace('<SPACE>', ' ')
                
            return {"text": text}
        elif filename.endswith(".docx"):
            import docx
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(para.text for para in doc.paragraphs)
            return {"text": text}
        elif filename.endswith(".txt") or filename.endswith(".md"):
            return {"text": content.decode("utf-8")}
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract text: {str(e)}")

@app.post("/api/skill-gap", response_model=SkillGapResponse)
async def skill_gap_endpoint(request: SkillGapRequest) -> SkillGapResponse:
    """
    Deep gap analysis for a selected or custom career pathway.
    
    Called when:
    - User clicks 'See skill gap ->' on a matched card (existing_skills + missing_skills populated)
    - User types a custom job title and clicks 'Analyze' (existing/missing may be empty)
    
    Returns full gap analysis including experience comparison and course recommendations.
    LLM results are cached for 1 hour by (cv_hash, target_title).
    """
    try:
        return await analyze_skill_gap(
            cv_text=request.cv_text,
            target_title=request.target_title,
            existing_skills=request.existing_skills,
            missing_skills=request.missing_skills,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Gap analysis is temporarily unavailable. Try again in a moment.",
        ) from exc

# Static frontend is mounted last so it never shadows the API routes
# registered above (Starlette matches routes in registration order).
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
