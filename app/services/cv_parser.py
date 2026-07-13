"""CV Parser — extracts structured data from unstructured CV text using an LLM.

Uses OpenRouter LLMs (configured in llm_utils.py) to parse chaotic CV text
into a clean, structured ParsedCV object.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
import re

from app.services.llm_utils import call_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class WeightedSkill:
    name: str
    weight: float
    source: str

@dataclass
class CandidateProfile:
    seniority: str = ""
    years_of_experience: str = ""
    domain: str = ""

@dataclass
class Education:
    degree: str = ""
    field_of_study: str = ""
    institution: str = ""
    year: str = ""
    raw_text: str = ""

@dataclass
class Experience:
    title: str = ""
    duration: str = ""
    years: float = 0.0
    description: str = ""
    inferred_skills: list[str] = field(default_factory=list)
    raw_text: str = ""

@dataclass
class Project:
    title: str = ""
    url: str = ""
    description: str = ""
    inferred_skills: list[str] = field(default_factory=list)
    raw_text: str = ""

@dataclass
class ParsedCV:
    profile: CandidateProfile = field(default_factory=CandidateProfile)
    skills: list[WeightedSkill] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def summary(self) -> str:
        parts = []
        if self.profile.seniority or self.profile.years_of_experience or self.profile.domain:
            parts.append(f"Profile: {self.profile.seniority} {self.profile.years_of_experience} {self.profile.domain}".strip())
        
        top_skills = [s.name for s in sorted(self.skills, key=lambda x: x.weight, reverse=True)[:15]]
        if top_skills:
            parts.append(f"Top Skills: {', '.join(top_skills)}")
            
        if self.experience:
            roles = [f"{e.title} ({e.duration})" for e in self.experience]
            parts.append(f"Experience: {', '.join(roles)}")
            
        if self.education:
            degrees = [f"{e.degree} in {e.field_of_study} from {e.institution}" for e in self.education]
            parts.append(f"Education: {', '.join(degrees)}")
            
        return "\n".join(parts) if parts else "No detailed profile could be extracted."

# ---------------------------------------------------------------------------
# Fallback Parser
# ---------------------------------------------------------------------------

def _fallback_parse(text: str) -> ParsedCV:
    """A dumb, safe regex fallback if the LLM completely fails."""
    logger.warning("Using regex fallback for CV parsing.")
    result = ParsedCV(raw_text=text)
    
    # Try to find words that look like skills (Capitalized, comma separated)
    # Just extracting chunks
    words = re.findall(r'\b[A-Z][a-zA-Z\s#\+\-\.]{2,20}\b', text)
    skills_set = set()
    for w in words:
        w = w.strip()
        if len(w) > 2 and w.lower() not in {"the", "and", "for", "with"}:
            skills_set.add(w)
            
    for s in list(skills_set)[:30]:
        result.skills.append(WeightedSkill(name=s, weight=0.5, source="fallback"))
        
    return result

# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

async def parse_cv(text: str) -> ParsedCV:
    if not text or not text.strip():
        return ParsedCV(raw_text=text)

    # Truncate text to avoid token limits (first ~4000 words is usually plenty)
    truncated_text = " ".join(text.split()[:4000])

    system_prompt = """You are an expert technical recruiter and resume parser.
Your job is to extract structured data from a raw, messy resume/CV text.
Always return your response as a valid JSON object matching the exact schema requested."""

    prompt = f"""
Please extract the following information from the provided CV text.

Return a JSON object with EXACTLY these keys:
- "profile": object with keys "seniority" (e.g. Junior, Senior), "years_of_experience" (e.g. "4"), "domain" (e.g. "Software Engineering").
- "skills": list of objects, each with "name" (string, e.g. "Python", "SQL", max 40 chars), "weight" (float, 1.0 for explicitly listed hard skills, 0.6 for inferred/soft skills), "source" (string, e.g. "explicit" or "inferred").
- "experience": list of objects, each with "title" (string), "duration" (string), "description" (string, max 300 chars).
- "education": list of objects, each with "degree" (string), "field_of_study" (string), "institution" (string), "year" (string).
- "certifications": list of strings.
- "languages": list of strings.

Only extract real, specific professional skills (tools, languages, frameworks, methodologies). Ignore generic filler words (e.g. "hard working", "team player").

CV TEXT:
\"\"\"
{truncated_text}
\"\"\"
"""

    try:
        parsed_json = await call_llm(prompt, system_prompt, timeout=15.0) #timeout=30.0
        
        result = ParsedCV(raw_text=text)
        
        # Populate Profile
        prof_data = parsed_json.get("profile", {})
        result.profile = CandidateProfile(
            seniority=prof_data.get("seniority", ""),
            years_of_experience=str(prof_data.get("years_of_experience", "")),
            domain=prof_data.get("domain", "")
        )
        
        # Populate Skills
        for s in parsed_json.get("skills", []):
            name = s.get("name", "")
            if len(name) > 40: continue # Sanity limit
            result.skills.append(WeightedSkill(
                name=name,
                weight=float(s.get("weight", 0.5)),
                source=s.get("source", "llm")
            ))
            
        # Deduplicate skills
        unique_skills = {}
        for s in result.skills:
            key = s.name.lower()
            if key not in unique_skills or s.weight > unique_skills[key].weight:
                unique_skills[key] = s
        result.skills = sorted(unique_skills.values(), key=lambda x: (-x.weight, x.name))
        
        # Populate Experience
        for e in parsed_json.get("experience", []):
            result.experience.append(Experience(
                title=e.get("title", ""),
                duration=e.get("duration", ""),
                description=e.get("description", "")
            ))
            
        # Populate Education
        for ed in parsed_json.get("education", []):
            result.education.append(Education(
                degree=ed.get("degree", ""),
                field_of_study=ed.get("field_of_study", ""),
                institution=ed.get("institution", ""),
                year=str(ed.get("year", ""))
            ))
            
        result.certifications = parsed_json.get("certifications", [])
        result.languages = parsed_json.get("languages", [])
        
        return result
        
    except Exception as e:
        logger.error(f"LLM parsing failed: {e}")
        return _fallback_parse(text)
