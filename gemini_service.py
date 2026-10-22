"""Gemini AI integration service for PipeManager.

Uses Python standard library (urllib.request) with zero external dependencies.
Connects to Google Gemini (gemini-1.5-flash / gemini-2.0-flash) to provide:
1. Semantic job posting analysis grounded in the candidate's real profile
2. Contextual, authentic email drafting tailored to the hiring manager and target role
3. Natural-language anti-slop auditing and rewriting
"""

import json
import os
import ssl
import urllib.error
import urllib.request

PRIMARY_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
FALLBACK_MODELS = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]


def clean_api_key(raw_key):
    """Sanitize API key by stripping quotes, whitespace, and pasted export prefixes."""
    if not raw_key:
        return ""
    k = str(raw_key).strip()
    if "=" in k and ("KEY" in k.upper() or "GEMINI" in k.upper()):
        k = k.split("=", 1)[1].strip()
    if k.lower().startswith("bearer "):
        k = k[7:].strip()
    return k.strip("\"'`; \t\n\r")


def get_api_key(profile=None):
    """Retrieve the Gemini API key from profile settings or environment."""
    if profile and profile.get("geminiApiKey"):
        return clean_api_key(profile["geminiApiKey"])
    return clean_api_key(os.environ.get("GEMINI_API_KEY", ""))


def is_available(profile=None):
    """Check if a Gemini API key is configured."""
    return bool(get_api_key(profile))


def _safe_urlopen(req, timeout=15):
    """Open request with SSL unverified context to prevent macOS cert bundle failures."""
    try:
        ctx = ssl._create_unverified_context()
    except Exception:
        ctx = None
    if ctx:
        return urllib.request.urlopen(req, timeout=timeout, context=ctx)
    return urllib.request.urlopen(req, timeout=timeout)


def _call_gemini_model(model_name, api_key, prompt, system_instruction=None, json_mode=False, timeout=20):
    clean_key = clean_api_key(api_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={clean_key}"
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

    with _safe_urlopen(req, timeout=timeout) as response:
        res_body = response.read().decode("utf-8")
        res_json = json.loads(res_body)
        candidates = res_json.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return ""


def _call_gemini_detailed(api_key, prompt, system_instruction=None, json_mode=False, timeout=25):
    """Call Google Gemini REST API with model fallback, returning (text, error)."""
    clean_key = clean_api_key(api_key)
    if not clean_key:
        return None, "Please enter your Gemini API key."

    models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    last_error = None

    for model in models_to_try:
        try:
            res = _call_gemini_model(model, clean_key, prompt, system_instruction, json_mode, timeout)
            if res:
                return res, None
        except urllib.error.HTTPError as err:
            raw_err = err.read().decode("utf-8", errors="replace")
            try:
                err_data = json.loads(raw_err)
                msg = err_data.get("error", {}).get("message", "")
            except Exception:
                msg = raw_err[:200]
            last_error = f"Google API (HTTP {err.code}): {msg or raw_err[:200]}"
            if err.code == 404:
                continue
            break
        except urllib.error.URLError as err:
            last_error = f"Network error connecting to Gemini API: {err.reason}"
            break
        except Exception as exc:
            last_error = f"Connection failed: {str(exc)}"
            break

    return None, last_error or "No response from Gemini models."


def _call_gemini(api_key, prompt, system_instruction=None, json_mode=False, timeout=20):
    """Call Google Gemini REST API with model fallback."""
    text, err = _call_gemini_detailed(api_key, prompt, system_instruction, json_mode, timeout)
    if err and not text:
        print(f"[Gemini API Call Failed]: {err}")
    return text


def test_api_key(api_key):
    """Verify an API key by testing live generation on Gemini models."""
    clean_key = clean_api_key(api_key)
    if not clean_key:
        return False, "Please enter your Gemini API key."

    # Strategy 1: Test generateContent on gemini-1.5-flash
    models_to_try = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]

    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={clean_key}"
        payload = json.dumps({"contents": [{"parts": [{"text": "Hello"}]}]}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with _safe_urlopen(req, timeout=12) as response:
                code = getattr(response, "status", None) or response.getcode()
                if code in (200, 201):
                    return True, f"Verified: Connected successfully to Gemini ({model})!"
        except urllib.error.HTTPError as err:
            raw_err = err.read().decode("utf-8", errors="replace")
            if err.code == 404:
                # Model endpoint not found, try next fallback model
                continue
            try:
                err_data = json.loads(raw_err)
                msg = err_data.get("error", {}).get("message", "")
                if "API_KEY_INVALID" in raw_err or "API key not valid" in msg:
                    return False, "Invalid API key. Please generate a new key at aistudio.google.com."
                return False, f"Google API ({err.code}): {msg or raw_err[:200]}"
            except Exception:
                return False, f"Authentication failed (HTTP {err.code}): {raw_err[:200]}"
        except urllib.error.URLError as err:
            return False, f"Network error connecting to Gemini API: {err.reason}"
        except Exception as exc:
            return False, f"Connection failed: {str(exc)}"

    # Strategy 2: Fallback to models catalog check
    catalog_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={clean_key}"
    catalog_req = urllib.request.Request(catalog_url, headers={"Content-Type": "application/json"}, method="GET")
    try:
        with _safe_urlopen(catalog_req, timeout=10) as response:
            code = getattr(response, "status", None) or response.getcode()
            if code in (200, 201):
                return True, "Verified: Connected successfully to Google Gemini API!"
    except urllib.error.HTTPError as err:
        raw_err = err.read().decode("utf-8", errors="replace")
        try:
            err_data = json.loads(raw_err)
            msg = err_data.get("error", {}).get("message", "")
            return False, f"Google API ({err.code}): {msg or 'Invalid API key'}"
        except Exception:
            return False, f"HTTP {err.code}: Authentication error"
    except Exception as exc:
        return False, f"Connection error: {str(exc)}"

    return False, "Could not authenticate with Gemini. Check your API key at aistudio.google.com."


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
- Experience: {years}+ years
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


def generate_company_description(company, context="", profile=None):
    """Generate a crisp, one-line description of what the company does."""
    api_key = get_api_key(profile)
    company_name = (company or "").strip()
    if not company_name:
        return "Innovative technology and enterprise solutions provider."

    if api_key:
        prompt = f"""Provide a crisp, professional, single-sentence (one line) description of what the company "{company_name}" does.
Keep it strictly under 25 words. Plain text only, no quotes, no markdown, no conversational filler.
Additional context if any: {context[:600]}
"""
        desc = _call_gemini(api_key, prompt, timeout=15)
        if desc:
            clean = desc.strip().strip('"\'`')
            if clean:
                return clean

    # Clean fallback if no API key or API call fails
    return f"{company_name} provides specialized solutions and enterprise services."


def suggest_contacts(company, role="", context="", profile=None):
    """Suggest key hiring points of contact (names and roles) for this opportunity."""
    api_key = get_api_key(profile)
    company_name = (company or "Company").strip()

    if api_key:
        prompt = f"""For a target opportunity at "{company_name}" (Target Role: {role or 'Professional'}), suggest 2-3 key hiring points of contact with name and role.
Return ONLY a valid JSON object matching this schema:
{{
  "contacts": [
    {{"name": "Hiring Manager", "role": "VP of Department / Hiring Lead", "email": ""}},
    {{"name": "Talent Partner", "role": "Senior Recruiter", "email": ""}}
  ]
}}
Context: {context[:600]}
"""
        raw = _call_gemini(api_key, prompt, json_mode=True, timeout=15)
        if raw:
            try:
                data = json.loads(raw)
                contacts = data.get("contacts", [])
                if isinstance(contacts, list) and contacts:
                    return contacts
            except Exception:
                pass

    return [
        {"name": "Hiring Manager", "role": "Department Head", "email": ""},
        {"name": "Talent Partner", "role": "Recruiter", "email": ""}
    ]


def generate_target_companies(profile=None, existing_companies=None, count=3):
    """Research and generate high-fit target companies for Max Mardan matching the search requirement.
    Income requirement is completely omitted. Generates `count` (default 3) verified companies at a time.

    Returns:
        tuple: (list_of_company_data_dicts, error_message)
    """
    api_key = get_api_key(profile)
    if not api_key:
        return None, "No Gemini API key is configured. Please enter and test your API key."

    name = (profile or {}).get("name") or "Max Mardan"
    summary = (profile or {}).get("backgroundSummary") or (
        "Sales, finance, customer service, event planning, market development, production. "
        "Former Rushable, Edward Jones, JPMorgan. Founded and sold two restaurants."
    )

    exclude_list = [c for c in (existing_companies or []) if c]
    exclude_text = ", ".join(exclude_list) if exclude_list else "None"

    system_instruction = (
        "You are an expert lead-research analyst executing the Company-Oriented Lead Search Requirement for PipeManager. "
        f"Find {count} distinct real, small, active boutique companies in New York City (or remote) where candidate Max Mardan could join as a valuable team member. "
        "Strictly adhere to the hard filters (NYC-based or remote, small size ~1 to 50 people, verifiable address, real people, working website). "
        "Target industries in strict priority: (1) Real estate development (ground-up, value-add, condo, multifamily, mixed-use; sales, leasing, marketing, investor relations), "
        "or (2) Event planning and production (corporate, galas, benefits, weddings, brand activations, AV, scenic/design). "
        "There is NO income or compensation requirement. Focus purely on company size, verifiable legitimacy, and operational fit. "
        "NEVER invent companies, fake people, fake URLs, or fake emails. Every detail must be factual."
    )

    user_prompt = f"""Find {count} distinct high-fit small TARGET COMPANIES for {name} based on the search requirement.

Candidate Verified Facts:
- Name: {name}
- Background: {summary}
- Strengths: Client-facing sales, relationship building, financial fluency, closing deals, personalized concierge service, event planning, production, quick response, fast learner.

Hard Filters (Drop any company that fails):
1. Location: NYC-based (Manhattan, Brooklyn, Queens, Bronx, Staten Island, or commutable NJ/Long Island) OR remote. Exclude firms neither NYC-based nor remote.
2. Size: Small boutique (approx. 1 to 50 people). Exclude massive global agencies, enterprise firms, or national chains.
3. Verifiable: Must be a real operating company with working website, real address, and named principals/founders.

Excluded Companies (ALREADY in pipeline - do NOT return any of these):
{exclude_text}

Format requirement:
Return ONLY a valid JSON object matching this schema with an array of {count} companies:
{{
  "companies": [
    {{
      "company": "Real Company Name",
      "website": "https://company-domain.com",
      "address": "Neighborhood or street address, New York, NY",
      "locationType": "NYC-based",
      "industry": "real estate development",
      "size": "Estimated headcount (e.g. 10-25 people)",
      "yearsInBusiness": "Years operating or founding year",
      "whatTheyDo": "One crisp line describing what the company does in their own terms",
      "targetRoleTitle": "Sales & Investor Relations / Business Development",
      "whyFit": "Cite exact facts from Max's background (Rushable, Edward Jones, JPMorgan, restaurant ownership, sales/finance)",
      "whyTheyWantMe": "The specific growth need Max fills and direct value brought",
      "legitimacyEvidence": "Named past projects, developments, or events with verifiable track record",
      "fitScore": 88,
      "contacts": [
        {{"name": "Founder or Managing Principal Name", "role": "Managing Principal / Founder", "email": "", "phone": ""}}
      ],
      "suggestedFirstMove": "One specific sentence for first outreach hook citing a project or mutual angle",
      "sources": ["https://company-domain.com"],
      "unverifiedItems": ["Details to verify on a call, e.g. exact current internal team size"],
      "firstCallQuestions": ["Targeted question to ask the company on the first call"]
    }}
  ]
}}
"""

    raw_json, err = _call_gemini_detailed(api_key, user_prompt, system_instruction=system_instruction, json_mode=True, timeout=35)
    if err or not raw_json:
        return None, err or "Failed to receive response from Gemini."

    try:
        import re
        clean = raw_json.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)
        parsed = json.loads(clean)
        
        items = []
        if isinstance(parsed, dict):
            if "companies" in parsed and isinstance(parsed["companies"], list):
                items = parsed["companies"]
            elif "company" in parsed:
                items = [parsed]
        elif isinstance(parsed, list):
            items = parsed

        valid_companies = [item for item in items if isinstance(item, dict) and item.get("company")]
        if not valid_companies:
            return None, "Gemini returned invalid or empty company list."
        return valid_companies, None
    except Exception as e:
        return None, f"Failed to parse Gemini output: {str(e)}"


def generate_target_company(profile=None, existing_companies=None):
    """Backwards-compatible helper returning a single company."""
    comps, err = generate_target_companies(profile, existing_companies, count=1)
    if err or not comps:
        return None, err
    return comps[0], None


def sync_lead_to_markdown(target_data, leads_path):
    """Synchronize generated target company or companies into docs/company_leads.md."""
    if not os.path.exists(leads_path):
        return
    try:
        import re
        if isinstance(target_data, dict):
            items = [target_data]
        elif isinstance(target_data, list):
            items = target_data
        else:
            return

        with open(leads_path, "r", encoding="utf-8") as f:
            content = f.read()

        for item in items:
            company_name = item.get("company", "Target Company")
            if company_name in content:
                continue

            nums = [int(n) for n in re.findall(r"### (\d+)\.", content)]
            next_num = max(nums, default=0) + 1

            industry = item.get("industry", "real estate development")
            based = item.get("address") or ("Manhattan" if "manhattan" in item.get("address", "").lower() else "NYC")
            size = item.get("size") or "1-50 people"
            priority = "High" if item.get("fitScore", 0) >= 85 else "Medium"

            ind_short = "Development" if "real estate" in industry.lower() else ("Events" if "event" in industry.lower() else "Other")
            new_row = f"| {next_num} | {company_name} | {ind_short} | {based} | {size} | New | {priority} |"

            lines = content.splitlines()
            table_idx = -1
            for idx, line in enumerate(lines):
                if line.startswith("|") and not line.startswith("| #") and not line.startswith("|---"):
                    table_idx = idx
            if table_idx != -1:
                lines.insert(table_idx + 1, new_row)
                content = "\n".join(lines)

            contacts = item.get("contacts") or []
            contact_str = contacts[0].get("name", "Not named") if contacts else "Not named"
            if contacts and contacts[0].get("role"):
                contact_role = contacts[0].get("role", "")
            if contact_role:
                contact_str += f" ({contact_role})"

            sources = item.get("sources") or []
            item_site = item.get('website', '')
            sources_str = " · ".join(f"[{s}]({s})" for s in sources) if sources else f"[{item_site}]({item_site})"

            block = f"""
### {next_num}. {company_name}
- **Status:** New · **Priority:** {priority}
- **Website:** {item.get("website", "Unverified")}
- **Based:** {based}
- **People:** {contact_str}
- **What they do:** {item.get("whatTheyDo", "")}
- **Why I fit:** {item.get("whyFit", "")}
- **Why they would want me:** {item.get("whyTheyWantMe", "")}
- **Evidence of legitimacy:** {item.get("legitimacyEvidence", "Unverified")}
- **Fit score:** {item.get("fitScore", 85)}/100
- **Contact:** {contact_str}
- **Next step:** {item.get("suggestedFirstMove", "Reach out to principal with project reference.")}
- **Sources:** {sources_str}
"""

            if "real estate" in industry.lower() and "## Real estate development" in content:
                parts = content.split("## Real estate development", 1)
                if "## New search results" in parts[1]:
                    subparts = parts[1].split("## New search results", 1)
                    content = parts[0] + "## Real estate development" + subparts[0] + block + "\n## New search results" + subparts[1]
                else:
                    content = content + "\n" + block
            elif "event" in industry.lower() and "## Event planning and production" in content:
                parts = content.split("## Event planning and production", 1)
                if "## Real estate development" in parts[1]:
                    subparts = parts[1].split("## Real estate development", 1)
                    content = parts[0] + "## Event planning and production" + subparts[0] + block + "\n## Real estate development" + subparts[1]
                else:
                    content = content + "\n" + block
            else:
                content = content + "\n" + block

        with open(leads_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"[sync_lead_to_markdown Error]: {e}")

