"""Truth-constrained match engine.

Scores a job posting against the verified candidate. When Gemini AI is configured,
it uses semantic reasoning to analyze requirements against the candidate's real profile.
Otherwise, it falls back to deterministic rule matching.
"""

import re
import candidate
import gemini_service

_YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*(?:or more\s+)?years?", re.IGNORECASE)
MAX_STORIES = 3


def _compile(keywords):
    parts = []
    for kw in keywords:
        prefix = kw.endswith("*")
        term = re.escape(kw.rstrip("*").lower())
        parts.append(term + (r"[a-z0-9]*" if prefix else ""))
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(parts) + r")(?![a-z0-9])")


def _hits(rule, text):
    return sorted({m.group(0) for m in rule.finditer(text)})


def _years_required(text):
    """Highest 'N+ years' figure in the text, or None."""
    found = [int(n) for n in _YEARS_RE.findall(text)]
    return max(found) if found else None


def analyze(text, basis="posting", profile=None):
    """Return {score, strengths, gaps, stories, basis, ...} for a job description.

    score is an int 0-100, or 0 when nothing in the text maps to the candidate.
    """
    if not (text and text.strip()):
        return {
            "score": 0,
            "basis": basis,
            "strengths": [],
            "gaps": [],
            "matched": [],
            "stories": [],
        }

    active_profile = profile or candidate.public_profile()

    # Try Gemini AI first if configured
    if gemini_service.is_available(active_profile) and basis != "template":
        gemini_res = gemini_service.analyze_posting(text, active_profile)
        if gemini_res:
            return gemini_res

    # Deterministic fallback matching
    lowered = text.lower()
    skills = active_profile.get("skills") or candidate.SKILLS
    gaps_def = active_profile.get("gaps") or candidate.GAPS
    years_exp = active_profile.get("yearsExperience") or candidate.YEARS_CLIENT_FACING

    matched = []
    for skill in skills:
        kws = skill.get("keywords") or [skill.get("label", "").lower()]
        rule = _compile(kws)
        hits = _hits(rule, lowered)
        if hits:
            matched.append({
                "key": skill.get("key", "skill"),
                "label": skill.get("label", "Skill"),
                "weight": skill.get("weight", 2),
                "evidence": skill.get("evidence", ""),
                "hits": hits
            })

    gaps = []
    for gap in gaps_def:
        kws = gap.get("keywords") or [gap.get("label", "").lower()]
        rule = _compile(kws)
        hits = _hits(rule, lowered)
        if hits:
            gaps.append({
                "key": gap.get("key", "gap"),
                "label": gap.get("label", "Requirement"),
                "weight": gap.get("weight", 1),
                "mitigation": gap.get("mitigation", ""),
                "hits": hits
            })

    years = _years_required(lowered)
    if years is not None and years > years_exp:
        gaps.append({
            "key": "years",
            "label": f"{years}+ years required",
            "weight": 2,
            "mitigation": f"The post asks for {years}+ years; profile shows {years_exp}+ years of experience. Lead with quantifiable outcomes, not tenure.",
            "hits": [f"{years}+ years"]
        })

    got = sum(m["weight"] for m in matched)
    missing = sum(g["weight"] for g in gaps)
    score = round(100 * got / (got + missing)) if got + missing else 0
    if score:
        score = max(20, min(score, 98))

    matched_keys = {m["key"] for m in matched}
    stories = active_profile.get("stories") or candidate.STORIES
    ranked = sorted(
        stories,
        key=lambda s: (-len(matched_keys & set(s.get("skills", []))), s.get("id", "")),
    )
    story_ids = [s["id"] for s in ranked if matched_keys & set(s.get("skills", []))][:MAX_STORIES]
    if not story_ids and stories:
        story_ids = [stories[0]["id"]]

    return {
        "score": score,
        "basis": basis,
        "strengths": [f"{m['label']}: {m['evidence']}" for m in matched],
        "gaps": [f"{g['label']}: {g['mitigation']}" for g in gaps],
        "matched": [{"label": m["label"], "hits": m["hits"]} for m in matched],
        "stories": story_ids,
    }
