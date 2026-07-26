import re
from typing import List, Tuple, Dict, Set

# Generic noise phrases or qualifiers to strip from 991-title corpus titles for SQL search
NOISE_PATTERNS = [
    r'\s*-\s*general education.*$',
    r'\s*-\s*general.*$',
    r'\s*\([^)]*\)',  # Anything in parenthesis e.g. (Entry Level)
    r'\s*-\s*entry level.*$',
    r'\s*-\s*senior level.*$',
]

# Negative domain exclusions to prevent cross-industry collisions
# e.g., A UX/UI/Graphic Design Lead shouldn't match an Interior Design or Construction Architect Lead
DOMAIN_EXCLUSIONS: Dict[str, List[str]] = {
    "ux": ["architect", "interior", "construction", "civil", "landscape"],
    "ui": ["architect", "interior", "construction", "civil", "landscape"],
    "graphic": ["architect", "interior", "construction", "civil"],
    "design lead": ["architect", "interior", "civil", "construction", "mechanical"],
    "art director": ["interior", "construction"],
}

STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "in", "of", "on", "at", "to",
    "with", "by", "from", "as", "is", "cum", "general"
}

def clean_target_title(target_title: str) -> str:
    """Strip noisy corpus qualifiers from target title."""
    if not target_title:
        return ""
    
    cleaned = target_title.strip()
    for pattern in NOISE_PATTERNS:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

def get_title_search_parameters(target_title: str) -> Tuple[str, List[str], List[str]]:
    """
    Extract search metadata for multi-tier querying:
    Returns:
    - clean_title: e.g. "Teacher" from "Teacher - General Education"
    - core_keywords: e.g. ["Art", "Director"] from "Art Director"
    - negative_keywords: e.g. ["interior", "architect"] for UX/Design leads
    """
    if not target_title:
        return "", [], []

    clean = clean_target_title(target_title)
    
    # Extract core keywords (words > 2 chars, ignoring stopwords)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', clean)
    core_keywords = [w for w in words if w.lower() not in STOPWORDS]
    
    # Check domain exclusions
    target_lower = target_title.lower()
    negative_keywords: Set[str] = set()
    
    for key, exclusions in DOMAIN_EXCLUSIONS.items():
        if key in target_lower:
            negative_keywords.update(exclusions)

    return clean, core_keywords, list(negative_keywords)
