"""Candidate profile management.

Serves as the single source of truth for matching, STAR stories, and email drafts.
Reads dynamically from the SQLite database so any job hunter can customize their
background, target role, comp, and Gemini API key via Parameter Edit.
"""

import json
import os
import db

NAME = "Candidate"
LOCATION = "Remote / Hybrid"
YEARS_CLIENT_FACING = 5
DEFAULT_TARGET_OTE = 150000

# Default skills fallback if database is empty
SKILLS = [
    {"key": "sales", "label": "Pipeline & Prospecting", "weight": 2,
     "keywords": ["prospecting", "outbound", "lead generation", "cold call*", "pipeline", "business development"],
     "evidence": "Demonstrated track record of prospecting, client acquisition, and closing business."},
    {"key": "closing", "label": "Demos & Closing", "weight": 2,
     "keywords": ["demo*", "closing", "close deals", "quota", "new business", "revenue"],
     "evidence": "Ran consultative discovery meetings, structured product demos, and closed new business against targets."},
    {"key": "accounts", "label": "Account Management", "weight": 1,
     "keywords": ["account management", "retention", "customer success", "relationship*", "upsell"],
     "evidence": "Managed client accounts with high satisfaction, retention, and account expansion."},
    {"key": "tools", "label": "CRM & Modern Tools", "weight": 1,
     "keywords": ["salesforce", "hubspot", "crm", "analytics", "tools"],
     "evidence": "Proficient in modern CRM, pipeline forecasting, and productivity tools."},
]

GAPS = []

STORIES = [
    {
        "id": "story-1",
        "title": "Exceeded Revenue Quota",
        "company": "Prior Role",
        "role": "Top Performer",
        "pitch": "Consistently outperformed quota through disciplined outbound prospecting and consultative discovery.",
        "skills": ["sales", "closing"],
        "situation": "Target required ramping revenue and signing new clients in a competitive market.",
        "task": "Build outbound momentum and secure high-value client commitments.",
        "action": "Implemented structured discovery, mapped stakeholder needs, and tailored value propositions.",
        "result": "Surpassed quarterly targets and expanded book of business.",
        "prompts": ["What specific objection did you overcome?", "What was the measurable revenue impact?"]
    }
]


def story_text(story):
    """Plain-text STAR note with prompts."""
    text = (f"Situation: {story.get('situation', '')}\nTask: {story.get('task', '')}\n"
            f"Action: {story.get('action', '')}\nResult: {story.get('result', '')}")
    if story.get("prompts"):
        text += "\nAdd your own detail: " + " / ".join(story["prompts"])
    return text


def story_by_id(story_id):
    """Look up a story by id from the database profile or fallback."""
    try:
        with db.connect() as conn:
            prof = db.get_profile_dict(conn)
            for s in prof.get("stories", []):
                if s.get("id") == story_id:
                    return s
    except Exception:
        pass
    for s in STORIES:
        if s.get("id") == story_id:
            return s
    return None


def skill_by_key(key):
    """Look up a skill by key."""
    try:
        with db.connect() as conn:
            prof = db.get_profile_dict(conn)
            for s in prof.get("skills", []):
                if s.get("key") == key:
                    return s
    except Exception:
        pass
    for s in SKILLS:
        if s.get("key") == key:
            return s
    return {"key": key, "label": key, "evidence": ""}


def public_profile():
    """Return the active candidate profile for the API and frontend."""
    try:
        with db.connect() as conn:
            prof = db.get_profile_dict(conn)
            if prof:
                stories = [{**s, "text": story_text(s)} for s in prof.get("stories", [])]
                return {
                    "name": prof.get("name") or "Candidate",
                    "email": prof.get("email") or "",
                    "headline": prof.get("headline") or "",
                    "location": prof.get("location") or "",
                    "targetRole": prof.get("targetRole") or "Account Executive",
                    "targetOte": prof.get("targetOte") or 150000,
                    "yearsExperience": prof.get("yearsExperience") or 5,
                    "backgroundSummary": prof.get("backgroundSummary") or "",
                    "skills": prof.get("skills") or SKILLS,
                    "stories": stories or STORIES,
                    "hasGeminiKey": prof.get("hasGeminiKey", False),
                    "geminiApiKeyMasked": prof.get("geminiApiKeyMasked", ""),
                }
    except Exception as e:
        print(f"[candidate.public_profile error]: {e}")

    return {
        "name": NAME,
        "email": "",
        "headline": "Target Role Candidate",
        "location": LOCATION,
        "targetRole": "Account Executive",
        "targetOte": DEFAULT_TARGET_OTE,
        "yearsExperience": YEARS_CLIENT_FACING,
        "backgroundSummary": "",
        "skills": SKILLS,
        "stories": [{**s, "text": story_text(s)} for s in STORIES],
        "hasGeminiKey": False,
        "geminiApiKeyMasked": "",
    }
