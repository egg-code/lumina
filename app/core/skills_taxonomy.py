import re
from typing import Dict, List, Set, Tuple

# Comprehensive taxonomy mapping skill variations/synonyms to a canonical representation
SKILL_ALIASES: Dict[str, List[str]] = {
    "google analytics": ["ga", "google web analytics", "web analytics", "google analytics 4", "ga4", "analytics"],
    "ui/ux design": ["ui/ux", "ux design", "ui design", "user experience", "user interface", "ux", "ui", "concept development"],
    "copywriting": ["content writing", "copy writing", "copywriter", "article writing", "content creation"],
    "content strategy": ["content strategist", "content marketing", "content planning"],
    "digital marketing": ["online marketing", "internet marketing", "performance marketing", "digital media"],
    "ms excel": ["excel", "microsoft excel", "spreadsheet", "advanced excel"],
    "ms office": ["office", "microsoft office", "ms word", "powerpoint"],
    "tally prime": ["tally", "tally erp", "tally erp 9", "tally prime", "accounting software"],
    "japanese": ["japanese language", "japanese speaking", "japanese speaker", "n1", "n2", "n3", "n4", "n5"],
    "english": ["english language", "english speaking", "fluent english", "business english"],
    "python": ["python3", "python programming", "django", "fastapi", "flask"],
    "machine learning": ["ml", "deep learning", "ai", "artificial intelligence", "data science"],
    "sql": ["postgresql", "mysql", "sqlite", "tsql", "plsql", "database"],
    "project management": ["project manager", "pmp", "agile project management", "scrum master"],
    "product management": ["product manager", "product owner", "product development"],
    "curriculum development": ["curriculum design", "lesson planning", "instructional design"],
    "classroom management": ["classroom instruction", "teaching", "student management"],
    "graphic design": ["branding and logo", "typography", "adobe illustrator", "photoshop", "canva", "design software"],
    "video editing": ["adobe premiere", "final cut", "final cut pro", "youtube studio", "video seo"],
}

# Reverse lookup dictionary: alias -> canonical key
_CANONICAL_MAP: Dict[str, str] = {}
for canonical, aliases in SKILL_ALIASES.items():
    _CANONICAL_MAP[canonical.lower()] = canonical.lower()
    for alias in aliases:
        _CANONICAL_MAP[alias.lower()] = canonical.lower()

# Generic soft skills that shouldn't artificially inflate specialized role scores
SOFT_SKILLS: Set[str] = {
    "communication", "verbal communication", "written communication",
    "teamwork", "team collaboration", "collaboration",
    "leadership", "leadership skills", "management",
    "writing", "active listening", "problem solving",
    "time management", "critical thinking", "interpersonal skills",
    "adaptability", "flexibility", "work ethic"
}

def normalize_skill(skill: str) -> str:
    """Clean and normalize a skill string."""
    if not skill:
        return ""
    cleaned = skill.strip().lower()
    # Strip common trailing noise
    cleaned = re.sub(r'[\(\)\[\]\{\}]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def get_canonical_skill(skill: str) -> str:
    """Map a skill string to its canonical representation if known."""
    norm = normalize_skill(skill)
    return _CANONICAL_MAP.get(norm, norm)

def is_soft_skill(skill: str) -> bool:
    """Check if a skill is classified as a generic soft skill."""
    norm = normalize_skill(skill)
    canon = get_canonical_skill(norm)
    return norm in SOFT_SKILLS or canon in SOFT_SKILLS

def check_skill_match(cand_skill: str, job_skill: str) -> bool:
    """Check if candidate skill matches job skill using taxonomy & substring rules."""
    c_norm = normalize_skill(cand_skill)
    j_norm = normalize_skill(job_skill)
    
    if not c_norm or not j_norm:
        return False
        
    if c_norm == j_norm:
        return True

    # Canonical match check
    c_canon = get_canonical_skill(c_norm)
    j_canon = get_canonical_skill(j_norm)
    if c_canon == j_canon:
        return True

    # Boundary search for non-trivial terms
    if len(c_norm) > 2 and len(j_norm) > 2:
        if c_norm in j_norm or j_norm in c_norm:
            return True

    return False

def calculate_weighted_fit(matched_skills: List[str], all_job_skills: List[str]) -> int:
    """
    Calculate a weighted skill fit score (0-100%) giving higher priority to technical/hard skills.
    Hard Skills: Weight 1.0
    Soft Skills: Weight 0.25
    """
    if not all_job_skills:
        return 50  # Default neutral score when no skills listed on job posting

    total_weight = 0.0
    matched_weight = 0.0

    matched_set = {normalize_skill(s) for s in matched_skills}

    for js in all_job_skills:
        weight = 0.25 if is_soft_skill(js) else 1.0
        total_weight += weight
        
        js_norm = normalize_skill(js)
        if any(check_skill_match(ms, js_norm) for ms in matched_skills):
            matched_weight += weight

    if total_weight == 0:
        return 50

    return int((matched_weight / total_weight) * 100)
