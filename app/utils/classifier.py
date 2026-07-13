"""Pure, network-free text formatting shared by the matching endpoints.

See engineering.md Section 5 for why this stays deterministic and
separate from any network call. v0.3: `validate_quotes` and
`merge_classification` — which merged an LLM classification against the
old closed 5-category set — are gone along with that flow (see git
history). `format_evidence_text` survives unchanged because it's just as
useful for the open-corpus `matched_terms` it's now fed (see
app/main.py's POST /api/match-titles) as it was for LLM-extracted quotes.
"""

from __future__ import annotations

FALLBACK_EVIDENCE_TEXT = (
    "We matched this from the overall shape of what you pasted, even though "
    "no single phrase jumped out on its own."
)


def format_evidence_text(terms: list[str]) -> str:
    """Build the rendered 'why this title' sentence from matched terms.

    Ported from the v0.1 prototype's `buildWhyText`, including its exact
    punctuation branches and zero-match fallback message. Originally fed
    LLM-extracted, CV-validated quotes; now fed the deterministic
    `matched_terms` produced by app/job_title_matcher.py's TF-IDF search —
    either way, every string passed in is guaranteed to actually appear in
    the CV text by the time it reaches here, so there's nothing left to
    validate at this layer.
    """
    top = terms[:3]
    if not top:
        return FALLBACK_EVIDENCE_TEXT

    parts = [f"“{t}”" for t in top]
    if len(parts) == 1:
        joined = parts[0]
    elif len(parts) == 2:
        joined = f"{parts[0]} and {parts[1]}"
    else:
        joined = f"{parts[0]}, {parts[1]}, and {parts[2]}"
    return f"We found {joined} across what you pasted — that’s a pattern, not a coincidence."
