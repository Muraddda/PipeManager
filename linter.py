"""Anti-slop linter: flags the stock phrases recruiters read as AI-written."""

import re

# phrase -> plainer replacement
SLOP = {
    "spearheaded": "led",
    "leveraged": "used",
    "leverage": "use",
    "delve": "look into",
    "testament": "proof",
    "multifaceted": "broad",
    "synergy": "teamwork",
    "game-changer": "big improvement",
    "pivotal": "key",
    "tapestry": "mix",
    "harnessing": "using",
    "cutting-edge": "modern",
    "deep dive": "close look",
    "passionate about": "care about",
    "results-driven": "focused on results",
    "proven track record": "record",
    "hit the ground running": "get productive fast",
    "self-starter": "start things myself",
    "go-getter": "driven",
    "think outside the box": "try new angles",
    "i am writing to express my interest": "I'm interested in",
    "thrilled": "glad",
    "rockstar": "strong performer",
}

_RULES = [
    (phrase, plain, re.compile(r"(?<![a-z])" + re.escape(phrase) + r"(?![a-z])", re.IGNORECASE))
    for phrase, plain in SLOP.items()
]


def lint(text):
    text = text or ""
    flagged = []
    cleaned = text
    for phrase, plain, rule in _RULES:
        if rule.search(text):
            flagged.append({"buzzword": phrase, "suggestion": plain})
            cleaned = rule.sub(plain, cleaned)
    return {
        "original": text,
        "cleaned": cleaned,
        "flaggedCount": len(flagged),
        "flagged": flagged,
        "humanAuthenticityScore": max(30, 100 - 10 * len(flagged)),
    }
