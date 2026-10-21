"""Email drafts built dynamically or generated via Gemini AI.

When Gemini AI is enabled, drafts are intelligently written to match the target
company, role, hiring manager, and candidate's verified achievements.
Otherwise, falls back to structured template generation.
"""

import candidate
import gemini_service


def _first(name):
    return name.split()[0] if name and name.strip() else "there"


def _pitches(opp, profile):
    stories = profile.get("stories") or candidate.STORIES
    ids = (opp.get("matchDetails") or {}).get("stories") or []
    found = [s for s in stories if s.get("id") in ids]
    if not found and stories:
        found = stories[:1]
    return [s.get("pitch", "") for s in found if s.get("pitch")] or ["I have a proven track record of delivering measurable revenue growth."]


def _backchannel(opp, profile):
    proof = opp.get("proofOfWork") or {}
    name = profile.get("name") or "Candidate"
    loc = profile.get("location") or ""
    sig = f"{name}\n{loc}".strip()

    if proof.get("artifactUrl"):
        offer = f"Instead of dropping a resume in the queue, I put together {proof.get('artifactName') or 'a one-page plan'} for the role: {proof['artifactUrl']}"
    else:
        offer = "Instead of dropping a resume in the queue, I can share a tailored 30-60-90 day plan for the role."

    pitches = _pitches(opp, profile)
    return {
        "subject": f"{opp.get('company')}: interested in the {opp.get('title')} role",
        "body": f"Hi {_first(opp.get('hiringManagerName'))},\n\n{pitches[0]}\n\n"
                f"I'm interested in the {opp.get('title')} role at {opp.get('company')}. {offer}\n\n"
                f"Do you have 10 minutes this week?\n\nBest,\n{sig}",
    }


def _followup(opp, profile):
    pitches = _pitches(opp, profile)
    extra = pitches[1] if len(pitches) > 1 else pitches[0]
    name = profile.get("name") or "Candidate"
    loc = profile.get("location") or ""
    sig = f"{name}\n{loc}".strip()

    return {
        "subject": f"Following up: {opp.get('title')} at {opp.get('company')}",
        "body": f"Hi {_first(opp.get('contactName'))},\n\nThanks for your time on the {opp.get('title')} role. "
                f"I'm still very interested in {opp.get('company')}. [One specific topic from our conversation.]\n\n"
                f"{extra}\n\nIs there anything else you need from me for the next step?\n\nBest,\n{sig}",
    }


def _thankyou(opp, profile):
    pitches = _pitches(opp, profile)
    name = profile.get("name") or "Candidate"
    loc = profile.get("location") or ""
    sig = f"{name}\n{loc}".strip()

    return {
        "subject": f"Thank you: {opp.get('title')} interview",
        "body": f"Hi {_first(opp.get('hiringManagerName'))},\n\nThank you for the time today. "
                f"[The question or topic that stuck with you most.] It made me more confident that {opp.get('company')} is where I want to work.\n\n"
                f"{pitches[0]}\n\nIf a sample plan or reference would help, I'm glad to send one.\n\nBest,\n{sig}",
    }


def _counter(opp, profile):
    pitches = _pitches(opp, profile)
    name = profile.get("name") or "Candidate"
    loc = profile.get("location") or ""
    sig = f"{name}\n{loc}".strip()

    target_val = int(opp.get("value") or profile.get("targetOte") or 150000)
    return {
        "subject": f"Offer discussion: {opp.get('title')}",
        "body": f"Hi {_first(opp.get('contactName'))},\n\nThank you for the offer for the {opp.get('title')} role at {opp.get('company')}. I'm excited about it.\n\n"
                f"{pitches[0]} With that track record, I'm targeting ${target_val:,} in total compensation. [Name the part of the offer you want to change.]\n\n"
                f"Could we talk for 10 minutes this week?\n\nBest,\n{sig}",
    }


TEMPLATES = {"backchannel": _backchannel, "followup": _followup, "thankyou": _thankyou, "counter": _counter}


def build(opp, template, target, profile=None):
    """Return {subject, body, to} for an opportunity dict."""
    active_profile = profile or candidate.public_profile()

    # Try Gemini AI first if configured
    if gemini_service.is_available(active_profile):
        gemini_draft = gemini_service.draft_email(opp, template, target, active_profile)
        if gemini_draft:
            return gemini_draft

    # Fallback template
    fn = TEMPLATES.get(template, _backchannel)
    draft = fn(opp, active_profile)
    draft["to"] = (opp.get("hiringManagerEmail") if target == "hm" else opp.get("contactEmail")) or ""
    return draft
