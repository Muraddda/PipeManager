"""Truth-constrained match engine.

Scores a job posting against the verified candidate. It only reports what the profile
supports (with the evidence) and what it lacks (with an honest mitigation). It never
invents experience, and it returns no score when the text mentions nothing it knows.
"""

import re

import candidate

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:or more\s+)?years?", re.IGNORECASE)
MAX_STORIES = 3


def _compile(keywords):
    parts = []
    for kw in keywords:
        prefix = kw.endswith("*")
        term = re.escape(kw.rstrip("*").lower())
        parts.append(term + (r"[a-z0-9]*" if prefix else ""))
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


_SKILL_RULES = [(s, _compile(s["keywords"])) for s in candidate.SKILLS]
_GAP_RULES = [(g, _compile(g["keywords"])) for g in candidate.GAPS]


def _hits(rule, text):
    return sorted({m.group(0) for m in rule.finditer(text)})


def _years_required(text):
    """Highest 'N+ years' figure in the text, or None."""
    found = [int(n) for n in _YEARS_RE.findall(text)]
    return max(found) if found else None


def analyze(text, basis="posting"):
    """Return {score, strengths, gaps, stories, basis, ...} for a job description.

    score is an int 0-100, or 0 when nothing in the text maps to the candidate.
    """
    lowered = (text or "").lower()

    matched = []
    for skill, rule in _SKILL_RULES:
        hits = _hits(rule, lowered)
        if hits:
            matched.append({"key": skill["key"], "label": skill["label"], "weight": skill["weight"],
                            "evidence": skill["evidence"], "hits": hits})

    gaps = []
    for gap, rule in _GAP_RULES:
        hits = _hits(rule, lowered)
        if hits:
            gaps.append({"key": gap["key"], "label": gap["label"], "weight": gap["weight"],
                         "mitigation": gap["mitigation"], "hits": hits})

    years = _years_required(lowered)
    if years is not None and years > candidate.YEARS_CLIENT_FACING:
        gaps.append({"key": "years", "label": f"{years}+ years required", "weight": 2,
                     "mitigation": f"The post asks for {years}+ years; the resume shows {candidate.YEARS_CLIENT_FACING}+ years of client-facing sales and advisory work since May 2020. Lead with results, not tenure.",
                     "hits": [f"{years}+ years"]})

    got = sum(m["weight"] for m in matched)
    missing = sum(g["weight"] for g in gaps)
    score = round(100 * got / (got + missing)) if got + missing else 0
    if score:
        score = max(20, min(score, 98))  # never claim a perfect match

    matched_keys = {m["key"] for m in matched}
    ranked = sorted(
        candidate.STORIES,
        key=lambda s: (-len(matched_keys & set(s["skills"])), s["id"]),
    )
    stories = [s["id"] for s in ranked if matched_keys & set(s["skills"])][:MAX_STORIES]

    return {
        "score": score,
        "basis": basis,
        "strengths": [f"{m['label']}: {m['evidence']}" for m in matched],
        "gaps": [f"{g['label']}: {g['mitigation']}" for g in gaps],
        "matched": [{"label": m["label"], "hits": m["hits"]} for m in matched],
        "stories": stories,
    }
