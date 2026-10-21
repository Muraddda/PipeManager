"""Email drafts built only from verified stories in candidate.py.

Placeholders in [brackets] mark details only the candidate can supply; the UI warns
until they are filled. No recipient address is ever guessed.
"""

import candidate

SIGNATURE = f"{candidate.NAME}\n{candidate.LOCATION}"
FALLBACK_STORY = "deposits"


def _first(name):
    return name.split()[0] if name and name.strip() else "there"


def _pitches(opp):
    ids = (opp.get("matchDetails") or {}).get("stories") or [FALLBACK_STORY]
    stories = [candidate.story_by_id(i) for i in ids]
    return [s["pitch"] for s in stories if s] or [candidate.story_by_id(FALLBACK_STORY)["pitch"]]


def _backchannel(opp):
    proof = opp.get("proofOfWork") or {}
    if proof.get("artifactUrl"):
        offer = f"Instead of dropping a resume in the queue, I put together {proof.get('artifactName') or 'a one-page plan'} for the role: {proof['artifactUrl']}"
    else:
        offer = "Instead of dropping a resume in the queue, I can send a one-page 30-60-90 day plan for the role."
    return {
        "subject": f"{opp['company']}: interested in the {opp['title']} role",
        "body": f"Hi {_first(opp.get('hiringManagerName'))},\n\n{_pitches(opp)[0]}\n\n"
                f"I'm interested in the {opp['title']} role at {opp['company']}. {offer}\n\n"
                f"Do you have 10 minutes this week?\n\nBest,\n{SIGNATURE}",
    }


def _followup(opp):
    pitches = _pitches(opp)
    extra = pitches[1] if len(pitches) > 1 else pitches[0]
    return {
        "subject": f"Following up: {opp['title']} at {opp['company']}",
        "body": f"Hi {_first(opp.get('contactName'))},\n\nThanks for your time on the {opp['title']} role. "
                f"I'm still very interested in {opp['company']}. [One specific thing from our conversation.]\n\n"
                f"{extra}\n\nIs there anything else you need from me for the next step?\n\nBest,\n{SIGNATURE}",
    }


def _thankyou(opp):
    return {
        "subject": f"Thank you: {opp['title']} interview",
        "body": f"Hi {_first(opp.get('hiringManagerName'))},\n\nThank you for the time today. "
                f"[The question or topic that stuck with you most.] It made me more confident that {opp['company']} is where I want to work.\n\n"
                f"{_pitches(opp)[0]}\n\nIf a sample plan or reference would help, I'm glad to send one.\n\nBest,\n{SIGNATURE}",
    }


def _counter(opp):
    return {
        "subject": f"Offer discussion: {opp['title']}",
        "body": f"Hi {_first(opp.get('contactName'))},\n\nThank you for the offer for the {opp['title']} role at {opp['company']}. I'm excited about it.\n\n"
                f"{_pitches(opp)[0]} With that track record, I'm targeting ${int(opp.get('value') or 0):,} in total compensation. [Name the part of the offer you want to change.]\n\n"
                f"Could we talk for 10 minutes this week?\n\nBest,\n{SIGNATURE}",
    }


TEMPLATES = {"backchannel": _backchannel, "followup": _followup, "thankyou": _thankyou, "counter": _counter}


def build(opp, template, target):
    """Return {subject, body, to} for an opportunity dict (API shape)."""
    fn = TEMPLATES[template]
    draft = fn(opp)
    draft["to"] = (opp.get("hiringManagerEmail") if target == "hm" else opp.get("contactEmail")) or ""
    return draft
