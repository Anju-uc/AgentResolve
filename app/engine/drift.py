"""Deterministic request/dispute drift signal. Supporting evidence only."""

import re
from difflib import SequenceMatcher
from app.models.forensics import DisputeDriftResult

_STOP = {"the","a","an","i","me","my","was","is","it","and","or","to","of","for","with","this","that","did","not"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOP and len(t) > 2}


def detect_dispute_drift(original: str, dispute: str) -> DisputeDriftResult:
    if not original or not dispute:
        return DisputeDriftResult()
    a = _tokens(original)
    b = _tokens(dispute)
    if not a or not b:
        return DisputeDriftResult(analyzed=True, similarity=0.0)
    similarity = SequenceMatcher(None, " ".join(sorted(a)), " ".join(sorted(b))).ratio()
    new_terms = sorted(b - a)
    # This is intentionally only a supporting signal; it never mutates attribution.
    return DisputeDriftResult(
        analyzed=True,
        similarity=round(similarity, 3),
        new_terms=new_terms[:20],
        likely_preference_drift=similarity < 0.45 and bool(new_terms),
    )
