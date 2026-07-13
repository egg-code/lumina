"""Pydantic data models shared across the backend.

v0.3 dropped the closed 5-category model in favor of matching over the
full ~1,000-title open corpus (`TitleMatch`, via app/job_title_matcher.py)
plus per-match sprint content generated live by Claude (`SprintResponse`,
via app/llm_client.py).

v0.4 drops that live generation step too — see action_steps.md #10. This
is an educational project with no budget for metered API costs, and a
Claude Pro/Max/Cowork subscription doesn't cover Claude API/Console
billing, so `app/llm_client.py` (and the `anthropic` dependency) is gone
entirely. `SprintRequest` now carries only `title` — no `cv_text` or
`matched_terms` — because `app/sprint_matcher.assign_sprint_content`
picks sprint content by matching `title` against a hand-authored
archetype library (`app/categories.ARCHETYPES`), the same free TF-IDF
technique `app/job_title_matcher.py` already uses for the title search
itself. `SprintResponse`'s shape is unchanged so the frontend didn't need
to change how it renders the result.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator

class LiveJob(BaseModel):
    job_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    job_link: Optional[str] = None
    required_skills: Optional[str] = None


class MatchTitlesRequest(BaseModel):
    """Incoming request body for POST /api/match-titles.

    This is the one "find my title" step now — see app/job_title_matcher.py.
    """

    cv_text: str = Field(min_length=30)
    top_n: int = Field(default=10, ge=1, le=50)


class TitleMatch(BaseModel):
    """One ranked job title from the ESCO occupations database.

    Now includes explicit gap analysis (existing vs missing skills) instead of
    opaque TF-IDF scores and matched terms.
    """

    title: str
    category: str
    match_score_percent: int
    existing_skills: list[str]
    missing_skills: list[str]
    
    # LLM-enriched fields
    why_fit: str = ""
    typical_timeframe: str = ""
    actionable_steps: list[str] = Field(default_factory=list)
    target_profile: str = ""
    why_this_person: str = ""
    search_keywords: list[str] = Field(default_factory=list)
    informational_interview_questions: list[str] = Field(default_factory=list)
    live_jobs: list[LiveJob] = Field(default_factory=list)
    
    # LLM-generated full sprint content
    sprint: list[str] = Field(default_factory=list)
    timeline: list[tuple[str, str]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)


class MatchTitlesResponse(BaseModel):
    """Response body for POST /api/match-titles.

    `source` and `corpus_size` are returned on every call so the frontend
    (or anyone inspecting the API) can see exactly what data produced the
    ranking — no scraped or personal data, a fixed public taxonomy only.
    """

    matches: list[TitleMatch]
    corpus_size: int
    source: str


class SprintRequest(BaseModel):
    """Incoming request body for POST /api/sprint.

    Just the title. There's no CV text or matched_terms here anymore —
    sprint content is assigned by nearest-archetype lookup on the title
    alone (app/sprint_matcher.py), not generated per-CV, so the backend
    has nothing else to do with them. See app/models.py's module
    docstring and action_steps.md #10 for why.
    """

    title: str = Field(min_length=1)


class SprintResponse(BaseModel):
    """Sprint/skills/timeline content for one matched job title.

    Shape (and the three validators below) is unchanged from the
    Claude-generation era, so the frontend's rendering code didn't need
    to change. Content now comes from whichever archetype
    app.sprint_matcher.assign_sprint_content picks for `title` — see
    app/categories.ARCHETYPES (or app.categories.DEFAULT_ARCHETYPE on a
    rare zero-overlap title) — not a live model call.
    """

    title: str
    examples: list[str]
    sprint: list[str]
    skills: list[str]
    timeline: list[tuple[str, str]]

    @field_validator("sprint")
    @classmethod
    def _sprint_has_seven_days(cls, value: list[str]) -> list[str]:
        if len(value) != 7:
            raise ValueError("sprint must have exactly 7 day-tasks")
        return value

    @field_validator("timeline")
    @classmethod
    def _timeline_has_three_phases(cls, value: list[tuple[str, str]]) -> list[tuple[str, str]]:
        if len(value) != 3:
            raise ValueError("timeline must have exactly 3 phases")
        return value

    @field_validator("examples")
    @classmethod
    def _examples_in_range(cls, value: list[str]) -> list[str]:
        if not (2 <= len(value) <= 3):
            raise ValueError("examples must have 2 or 3 entries")
        return value

class SkillGapItem(BaseModel):
    name: str
    severity: str               # "critical" | "nice_to_have"
    category: str               # "technical" | "soft" | "domain" | "tool"
    user_has_equivalent: bool   # True if user's CV has a close semantic match
    equivalent_skill: str = ""  # e.g. "Pandas" ≈ "Data Analysis"

class CourseResource(BaseModel):
    title: str
    provider: str               # "Coursera", "freeCodeCamp", "YouTube", etc.
    url: str                    # Best-effort URL (may 404 occasionally)
    duration_hours: Optional[int] = None
    cost: str                   # "Free" | "Free audit" | "Paid"
    format: str                 # "video" | "interactive" | "book" | "practice"
    difficulty: str             # "beginner" | "intermediate" | "advanced"

class SkillRecommendation(BaseModel):
    skill_name: str
    priority: int               # 1 = most critical to learn first
    reason: str                 # Why this skill matters for the role (1 sentence)
    resources: list[CourseResource]  # 2-3 resources, free-first order

class ExperienceGap(BaseModel):
    area: str                   # e.g. "Client-facing project delivery"
    user_has: str               # e.g. "4 years running paid social campaigns"
    role_needs: str             # e.g. "Software project lifecycle management"
    bridge_note: str            # How user can leverage their existing experience
    relevance_score: int        # 1-10, how relevant this gap is (used for sorting)

class SkillGapRequest(BaseModel):
    cv_text: str = Field(min_length=30)
    target_title: str = Field(min_length=2)
    # These come from /api/match-titles if user picked a matched card,
    # or are left empty [] if user typed a custom role
    existing_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

class SkillGapResponse(BaseModel):
    target_title: str
    match_score_percent: int            # 0-100
    readiness_label: str               # "Ready Now" | "3-6 months" | "6-12 months" | "1+ year"
    total_learning_hours_estimate: int
    # Skill sections
    overlapping_skills: list[str]
    missing_skills_detail: list[SkillGapItem]
    excess_skills: list[str]
    # Experience comparison (3-5 most relevant, LLM-selected)
    experience_gaps: list[ExperienceGap]
    # Learning pathway
    recommendations: list[SkillRecommendation]
    # Source/quality flag
    enriched_by_llm: bool = True       # False = ESCO fallback only, no courses

