"""Max Mardan's verified background: the single source of truth for matching and drafting.

Every fact below comes from the resume. Nothing here is estimated or embellished.
Contact details live in profile.local.json (gitignored) so they never reach the repo.
Stories carry `prompts`: details only the candidate knows, to add before an interview.
"""

import json
import os

LOCAL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.local.json")

NAME = "Max Mardan"
LOCATION = "New York, NY"
# Client-facing sales and advisory work since May 2020 (Rushable, Edward Jones, JPMorgan).
YEARS_CLIENT_FACING = 6
DEFAULT_TARGET_OTE = 150000  # editable placeholder, not a market claim

# A skill is matched when any keyword appears in the job text. A trailing * means prefix match.
# weight: how much the skill counts toward the match score.
SKILLS = [
    {"key": "consultative", "label": "Consultative selling", "weight": 2,
     "keywords": ["consultative", "solution selling", "solutions selling", "discovery", "needs analysis", "value selling"],
     "evidence": "Ran consultative client meetings at JPMorgan Chase and Edward Jones, recommending deposit, credit and investment products."},
    {"key": "prospecting", "label": "B2B prospecting", "weight": 2,
     "keywords": ["prospecting", "outbound", "lead generation", "cold call*", "sdr", "bdr", "pipeline generation", "business development", "new logo*"],
     "evidence": "Prospected 10 to 15 leads a day at Rushable and signed 108 new clients."},
    {"key": "closing", "label": "Demos and closing", "weight": 2,
     "keywords": ["demo*", "closing", "close deals", "full-cycle", "full cycle", "quota", "new business", "hunter", "carry a number"],
     "evidence": "Ran demos and closed 108 clients ($21.5K MRR); led the team past quota every month from Jul 2022 to Jan 2023."},
    {"key": "leadership", "label": "Sales team leadership", "weight": 2,
     "keywords": ["sales leadership", "team lead", "player-coach", "manage a team", "managing a team", "director", "coach*", "sales management", "territory manager*", "hiring"],
     "evidence": "Promoted to Director of Sales in two years; led 7 territory managers and 25 SDRs nationwide."},
    {"key": "fintech", "label": "Financial products", "weight": 2,
     "keywords": ["fintech", "financial services", "payments", "banking", "lending", "credit", "deposit*", "wealth", "investment*", "retirement", "treasury", "cards", "mortgage*"],
     "evidence": "Moved $10M+ of idle deposits into investments, facilitated $2M+ in business lines of credit and 3 mortgages at JPMorgan."},
    {"key": "licenses", "label": "FINRA licenses", "weight": 1,
     "keywords": ["series 7", "series 66", "finra", "licensed", "regulated", "compliance"],
     "evidence": "Holds FINRA Series 7 and Series 66."},
    {"key": "gtm", "label": "Market building", "weight": 1,
     "keywords": ["go-to-market", "gtm", "new market*", "market expansion", "greenfield", "0 to 1", "zero to one", "launch*", "build from scratch"],
     "evidence": "Built the Manhattan market and office at Rushable from scratch."},
    {"key": "smb", "label": "SMB and restaurant sector", "weight": 1,
     "keywords": ["smb", "small business*", "restaurant*", "hospitality", "merchant*", "food service", "local business*", "main street"],
     "evidence": "Sold to restaurants and small businesses at Rushable; founded, ran and sold two restaurants."},
    {"key": "accounts", "label": "Account management", "weight": 1,
     "keywords": ["account management", "book of business", "customer success", "retention", "portfolio", "upsell", "cross-sell", "expansion", "renewal*"],
     "evidence": "Managed 133 accounts across NY metro at Rushable and co-managed $5.5M across 63 clients at Edward Jones."},
    {"key": "crm", "label": "CRM and pipeline tools", "weight": 1,
     "keywords": ["salesforce", "hubspot", "crm", "pipeline management", "forecast*"],
     "evidence": "Works in Salesforce and HubSpot."},
    {"key": "analytics", "label": "Reporting and analytics tools", "weight": 1,
     "keywords": ["tableau", "sas", "analytics", "reporting", "data-driven", "excel", "quickbooks"],
     "evidence": "Tools: Tableau, SAS, QuickBooks, Microsoft Office."},
    {"key": "founder", "label": "Founder and operator", "weight": 1,
     "keywords": ["entrepreneur*", "founder", "ownership", "startup*", "scrappy", "builder", "p&l", "operations"],
     "evidence": "Took two restaurants from lease to opening, ran them profitably, and sold both ($35K lease to $90K; $115K to $250K)."},
    {"key": "mandarin", "label": "Mandarin Chinese", "weight": 1,
     "keywords": ["mandarin", "chinese", "bilingual", "apac", "cantonese"],
     "evidence": "Fluent in Mandarin Chinese and English."},
    {"key": "relationships", "label": "Client relationships", "weight": 1,
     "keywords": ["relationship*", "trusted advisor", "c-level", "executive presence", "client satisfaction", "customer-obsessed", "customer obsessed"],
     "evidence": "Held a 90%+ client satisfaction rating at JPMorgan."},
    {"key": "partnership", "label": "Cross-functional partnership", "weight": 1,
     "keywords": ["cross-functional", "collaborat*", "partner with", "stakeholder*"],
     "evidence": "Partnered with financial advisors, business bankers and mortgage specialists through close."},
]

# Things job posts ask for that the resume does not show. Each carries an honest counter-narrative.
GAPS = [
    {"key": "enterprise", "label": "Enterprise SaaS quota", "weight": 2,
     "keywords": ["enterprise", "saas", "arr", "mid-market", "multi-thread*", "complex sales", "strategic accounts"],
     "mitigation": "No enterprise SaaS quota on the resume. Closest proof: recurring-revenue B2B selling at Rushable (108 clients, $21.5K MRR). Say so directly and lead with that."},
    {"key": "technical", "label": "Technical or API fluency", "weight": 1,
     "keywords": ["api*", "developer*", "technical sales", "solutions engineer*", "sql", "integration*", "sales engineer*"],
     "mitigation": "No engineering background listed. Show you learn products fast: you hold Series 7 and Series 66 and recommended deposit, credit and investment products to clients. Ask for a technical ramp plan."},
    {"key": "methodology", "label": "Named sales methodology", "weight": 1,
     "keywords": ["meddpicc", "meddic", "challenger", "spin selling", "sandler"],
     "mitigation": "Not listed. Describe your discovery process in your own words and offer to be certified in theirs."},
    {"key": "salestools", "label": "Sales engagement tools", "weight": 1,
     "keywords": ["outreach.io", "salesloft", "gong", "apollo", "zoominfo", "sales navigator", "clari"],
     "mitigation": "Not listed. You already run pipeline in Salesforce and HubSpot; these tools are a short ramp."},
]

STORIES = [
    {"id": "market-build", "pitch": "At Rushable I built the Manhattan market from scratch and signed 108 new clients worth $21.5K in monthly recurring revenue.", "title": "Built the Manhattan market from scratch (Rushable)",
     "skills": ["gtm", "prospecting", "closing", "smb", "accounts"],
     "situation": "Rushable had no Manhattan market or office.",
     "task": "Open the market and grow it into a real book of business.",
     "action": "Prospected 10 to 15 restaurants and small businesses a day, ran demos, and managed 133 accounts across NY metro.",
     "result": "Signed 108 new clients worth $21.5K in monthly recurring revenue (about $972K estimated total value) and was promoted to Director in two years.",
     "prompts": ["What was your first-week outreach routine?", "Name the deal you remember best and why it closed."]},
    {"id": "director-team", "pitch": "As Director of Sales at Rushable I led 7 territory managers and 25 SDRs, and the team beat quota every month from July 2022 to January 2023.", "title": "Led 7 territory managers and 25 SDRs past quota (Rushable)",
     "skills": ["leadership", "closing", "prospecting"],
     "situation": "You were promoted to Director of Sales at Rushable.",
     "task": "Hit quota with a team spread across territories and SDRs.",
     "action": "Led 7 territory managers and 25 SDRs nationwide.",
     "result": "The team beat quota every month from Jul 2022 to Jan 2023.",
     "prompts": ["What did you change in how the team worked?", "Describe one rep you coached and what improved."]},
    {"id": "restaurants", "pitch": "I bought, built and sold two restaurants, turning a $35K lease into a $90K sale and a $115K lease into a $250K sale.", "title": "Bought, built and sold two restaurants (Sama, Eden Silk Road)",
     "skills": ["founder", "smb", "gtm", "leadership"],
     "situation": "You opened two restaurants in Fremont, CA.",
     "task": "Take each restaurant from lease to opening, then to a profitable sale.",
     "action": "Handled licenses, permits and paperwork, managed contractors, set up the finances, ran front of house, trained staff, and put in operating systems and promotions.",
     "result": "Bought the first lease for $35K and sold for $90K; bought the second for $115K and sold for $250K.",
     "prompts": ["What was the hardest permit or contractor problem?", "Why did you choose to sell each one?"]},
    {"id": "deposits", "pitch": "At JPMorgan I moved $10M+ of idle client deposits into investments and held a 90%+ client satisfaction rating.", "title": "Moved $10M+ in idle deposits into investments (JPMorgan)",
     "skills": ["consultative", "fintech", "relationships", "licenses"],
     "situation": "Clients held large balances in idle deposits.",
     "task": "Recommend the right deposit, credit and investment products for each client.",
     "action": "Ran consultative meetings in person and by phone, then recommended products that fit each client's goals.",
     "result": "Moved $10M+ into investments, facilitated $2M+ in business lines of credit and 3 mortgages, held a 90%+ client satisfaction rating, and beat commission guidelines by 50% month to month.",
     "prompts": ["Walk through one client conversation from first question to close.", "How did you handle a client who said no?"]},
    {"id": "advisor-book", "pitch": "At Edward Jones I co-managed $5.5M in retirement assets across 63 clients and added about 3 new clients a month.", "title": "Grew a $5.5M retirement book across 63 clients (Edward Jones)",
     "skills": ["accounts", "consultative", "fintech", "licenses", "relationships"],
     "situation": "You joined as a new financial advisor and co-managed a client book.",
     "task": "Grow assets and clients while meeting every new-advisor goal.",
     "action": "Assessed client goals, built personalized investment and retirement strategies, adjusted them over time, and ran community workshops on financial planning.",
     "result": "Co-managed $5.5M across 63 clients, added about $100K in new assets and 3 new clients a month on average, and met or beat every new-advisor goal.",
     "prompts": ["How did the workshops turn into clients?", "What did you adjust for a client when markets moved?"]},
    {"id": "cross-team", "pitch": "At JPMorgan I partnered with financial advisors, business bankers and mortgage specialists to facilitate $2M+ in business lines of credit and 3 mortgages.", "title": "Closed deals across specialists (JPMorgan)",
     "skills": ["partnership", "fintech", "relationships"],
     "situation": "Client needs can span products owned by different specialists.",
     "task": "Get the client the right specialist at the right time without losing the relationship.",
     "action": "Partnered with financial advisors, business bankers and mortgage specialists through close.",
     "result": "Facilitated $2M+ in business lines of credit and 3 mortgages alongside the investment results.",
     "prompts": ["Describe a handoff that went well and one that did not."]},
]

_BY_KEY = {s["key"]: s for s in SKILLS}
_STORY_BY_ID = {s["id"]: s for s in STORIES}


def skill_by_key(key):
    return _BY_KEY[key]


def story_by_id(story_id):
    return _STORY_BY_ID.get(story_id)


def story_text(story):
    """Plain-text STAR note, with the prompts that still need the candidate's own detail."""
    text = (f"Situation: {story['situation']}\nTask: {story['task']}\n"
            f"Action: {story['action']}\nResult: {story['result']}")
    if story.get("prompts"):
        text += "\nAdd your own detail: " + " / ".join(story["prompts"])
    return text


def load_local():
    try:
        with open(LOCAL_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def public_profile():
    local = load_local()
    return {
        "name": NAME,
        "location": LOCATION,
        "email": local.get("email", ""),
        "yearsClientFacing": YEARS_CLIENT_FACING,
        "skills": [{"key": s["key"], "label": s["label"], "evidence": s["evidence"]} for s in SKILLS],
        "stories": [{**s, "text": story_text(s)} for s in STORIES],
    }
