"""Gemini AI integration service for PipeManager.

Uses Python standard library (urllib.request) with zero external dependencies.
Connects to Google Gemini (gemini-2.5-flash) to provide:
1. Semantic job posting analysis grounded in the candidate's real profile
2. Contextual, authentic email drafting tailored to the hiring manager and target role
3. Natural-language anti-slop auditing and rewriting
"""

import json
import os
import urllib.error
import urllib.request

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_BASE_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def get_api_key(profile=None):
    """Retrieve the Gemini API key from profile settings or environment."""
    if profile and profile.get("geminiApiKey"):
        return profile["geminiApiKey"].strip()
    return os.environ.get("GEMINI_API_KEY", "").strip()


def is_available(profile=None):
    """Check if a Gemini API key is configured."""
    return bool(get_api_key(profile))


def _call_gemini(api_key, prompt, system_instruction=None, json_mode=False, timeout=20):
    """Call Google Gemini REST API using urllib.request."""
    if not api_key:
        return None

    url = f"{GEMINI_BASE_URL}?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2 if json_mode else 0.4,
        }
    }

    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            candidates = res_json.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            return ""
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode("utf-8", errors="replace")
        print(f"[Gemini API HTTPError {err.code}]: {err_msg}")
        return None
    except Exception as exc:
        print(f"[Gemini API Exception]: {exc}")
        return None


def test_api_key(api_key):
    """Verify an API key by making a minimal test call."""
    if not api_key:
        return False, "API key is required"
    res = _call_gemini(api_key, "Respond with: ok", timeout=10)
    if res is not None:
        return True, "API Key is valid and active"
    return False, "Could not authenticate with Gemini API. Check your key."


def _build_system_grounding(profile):
    """Build a truthful system prompt grounded in candidate facts."""
    name = profile.get("name") or "Candidate"
    role = profile.get("targetRole") or profile.get("headline") or "Professional"
    years = profile.get("yearsExperience") or 5
    location = profile.get("location") or "Remote / Hybrid"
    summary = profile.get("backgroundSummary") or profile.get("headline") or ""
    skills = profile.get("skills") or []
    stories = profile.get("stories") or []

    skills_text = "\n".join([f"- {s.get('label', s.get('key', 'Skill'))}: {s.get('evidence', '')}" for s in skills]) if skills else "Experienced professional in core competencies."
    stories_text = "\n".join([f"- {st.get('title')}: {st.get('pitch') or st.get('situation', '')}" for st in stories]) if stories else "Demonstrated career track record."

    return f"""You are the truth-grounded career intelligence engine for {name}.
Candidate Profile:
- Target Role: {role}
- Client/Work Experience: {years}+ years
- Location: {location}
- Professional Background: {summary}

Verified Strengths & Evidence (NEVER hallucinate or invent past claims):
{skills_text}

Verified Achievements & STAR Stories:
{stories_text}

Rules:
1. Ground every claim directly in the candidate's real profile.
2. If the posting asks for skills not in the background, report them as honest gaps with a constructive ramp plan.
3. Keep tone authentic, crisp, and executive-ready. Avoid corporate buzzwords (spearheaded, synergy, rockstar, leveraged).
"""


def analyze_posting(text, profile):
    """Score and analyze a job posting using Gemini."""
    api_key = get_api_key(profile)
    if not api_key:
        return None

    system_prompt = _build_system_grounding(profile)
    user_prompt = f"""Analyze this job posting against the candidate's verified profile.
Return a valid JSON object matching this exact schema:
{{
  "score": integer between 20 and 96,
  "strengths": ["Strength 1 citing candidate evidence", "Strength 2 citing candidate evidence", ...],
  "gaps": ["Requirement from post: honest mitigation or ramp plan", ...],
  "matched": [{{"label": "Skill Category", "hits": ["keywords found in text"]}}],
  "stories": ["story-id-or-title", ...]
}}

Job Posting:
{text}
"""

    raw_json = _call_gemini(api_key, user_prompt, system_instruction=system_prompt, json_mode=True)
    if not raw_json:
        return None

    try:
        data = json.loads(raw_json)
        score = int(data.get("score", 75))
        score = max(20, min(score, 98))
        return {
            "score": score,
            "basis": "gemini",
            "strengths": data.get("strengths", []),
            "gaps": data.get("gaps", []),
            "matched": data.get("matched", []),
            "stories": data.get("stories", []),
        }
    except Exception as e:
        print(f"[Gemini Parse Error]: {e}")
        return None


def draft_email(opp, template_type, target_role, profile):
    """Generate a high-converting, authentic email draft using Gemini."""
    api_key = get_api_key(profile)
    if not api_key:
        return None

    system_prompt = _build_system_grounding(profile)
    company = opp.get("company", "Company")
    title = opp.get("title", "Role")
    recipient_name = opp.get("hiringManagerName") if target_role == "hm" else opp.get("contactName")
    recipient_email = (opp.get("hiringManagerEmail") if target_role == "hm" else opp.get("contactEmail")) or ""
    target_comp = opp.get("value", 0)
    job_reqs = (opp.get("jobDetails") or {}).get("requirements", "")

    strategy_instructions = {
        "backchannel": "Draft a concise, high-impact cold outreach note to the Hiring Manager offering a 30-60-90 day execution plan.",
        "followup": "Draft a polite, confident follow-up email after an initial screen, reinforcing fit with a specific verified achievement.",
        "thankyou": "Draft a thoughtful, executive post-interview thank you email connecting conversation points to past results.",
        "counter": f"Draft an appreciative, professional offer negotiation email anchoring compensation toward ${target_comp:,} based on proven track record.",
    }

    inst = strategy_instructions.get(template_type, "Draft an outreach email for this opportunity.")

    user_prompt = f"""{inst}
Target Opportunity:
- Company: {company}
- Role: {title}
- Recipient: {recipient_name or ('Hiring Manager' if target_role == 'hm' else 'Talent Partner')}
- Target Comp: ${target_comp:,}
- Key Job Requirements: {job_reqs[:1200]}

Format requirement:
Return ONLY a valid JSON object:
{{
  "subject": "Clear, compelling email subject",
  "body": "Complete email body including greeting and sign-off from {profile.get('name', 'Candidate')}. Do NOT leave any bracketed placeholders like [insert date] - write complete text."
}}
"""

    raw_json = _call_gemini(api_key, user_prompt, system_instruction=system_prompt, json_mode=True)
    if not raw_json:
        return None

    try:
        data = json.loads(raw_json)
        return {
            "subject": data.get("subject", f"{company}: {title} role inquiry"),
            "body": data.get("body", ""),
            "to": recipient_email,
        }
    except Exception as e:
        print(f"[Gemini Draft Parse Error]: {e}")
        return None


def lint_text(text, profile):
    """Audit email wording for authenticity using Gemini."""
    api_key = get_api_key(profile)
    if not api_key:
        return None

    user_prompt = f"""Review this job hunt outreach email for authenticity, corporate buzzwords, and robotic AI phrasing.
Text to review:
\"\"\"{text}\"\"\"

Return a valid JSON object:
{{
  "humanAuthenticityScore": integer 0-100,
  "flaggedCount": integer,
  "flagged": [{{"buzzword": "flagged phrase", "suggestion": "plain human replacement"}}],
  "cleaned": "Complete rewritten version in crisp, natural, human voice"
}}
"""

    raw_json = _call_gemini(api_key, user_prompt, json_mode=True)
    if not raw_json:
        return None

    try:
        return json.loads(raw_json)
    except Exception as e:
        print(f"[Gemini Lint Parse Error]: {e}")
        return None
