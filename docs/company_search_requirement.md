# Company-Oriented Lead Search Requirement (PipeManager)

Paste everything below the line into any AI with web search (Claude, Gemini, ChatGPT) or execute directly via Gemini API. Save results into `company_leads.md`.

---

## ROLE
You are a lead-research analyst. Find small COMPANIES where I could join as a valuable team member. Do not search job boards for open roles. A company is a lead even if it has no posting, as long as it fits with below. Always generate 3 verified companies at a time.

## ABOUT ME (verified facts only; do not invent or inflate)
- Name: Max Mardan
- Background: sales and finance, customer service, event planning, market development, production
- Previous Employers: Rushable, Edward Jones, JPMorgan. Founded and sold two restaurants.
- Strengths: client-facing sales, relationship building, financial fluency, closing deals, personalized concierge service, event planning, production, quick response, fast learner

## HARD FILTERS (drop any company that fails one)
1. **Location:** Based in the New York City area (Manhattan, Brooklyn, Queens, Bronx, Staten Island, near NJ/Long Island only if the office is commutable), **or** a company that hires remote. Say which one applies to each result. Exclude firms that are neither NYC-based nor remote.
2. **Small size:** about 1 to 50 people. Verify from the team page, LinkedIn or a directory. Exclude global agencies, national chains and large enterprises. If size is unknown, say so and rank lower.
3. **Verifiable:** real address, named people and a working website. Exclude MLM models, pay-to-join fees and income-claim-only pitches.

## TARGET INDUSTRIES (preference order)
1. Real estate development (ground-up, value-add, condo, multifamily, mixed-use; sales, leasing, marketing and investor relations all count)
2. Event planning and event production (corporate, galas, benefits, weddings, brand activations, AV, scenic and design)
3. **Other industries only if the preferences above can't be met.** First fill the list from industries 1 and 2. If fewer than 10 verified companies pass the filters, add companies from other industries where my background fits (client-facing sales, concierge-style service, finance-adjacent work, production). Label each one "other industry" and say why it fits.

## WHAT MAKES A COMPANY A STRONG FIT (rank higher)
1. It has a growth need I can fill: new client acquisition, sales and leasing support, buyer or investor relations, client concierge, or production coordination.
2. It values entrepreneurs and fast learners over industry tenure. Look for founder-led firms, family-owned firms, and "our team" pages with a small headcount.
3. It has real traction: named projects or events, years in business, press, reviews, named clients or sponsors.

## SEARCH METHOD (Optimized for Gemini Search & Grounding)
1. Query formulation strategy:
   - Real estate development: `"boutique real estate developer" "New York" "team"`, `"condo developer" sales leasing Manhattan OR Brooklyn`, `"family-owned developer" NYC`, NYC development project news, boutique commercial/residential developer directories.
   - Event planning & production: `"boutique event production company" "New York"`, `"corporate event planner" NYC team founders`, `"experiential design" boutique agency Brooklyn Manhattan`, trade awards and vendor showcases.
2. Verification protocol:
   - Ground every finding in live web results and official company web pages.
   - Cross-check company domain, headquarters address, team member names, and confirmed projects.
   - Deduplicate against existing pipeline leads: Skip companies already in `company_leads.md` (e.g., Adam America Real Estate, Untouchable Events, EMRG Media, David Stark Design, Colin Cowie Lifestyle, MKG, Jack Morton, HB Capital).
3. Return 3 verified companies at a time ranked by fit score (preferred industries first).

## OUTPUT FORMAT

### 1. Markdown Block (For pasting into `company_leads.md`)
- **Company / Website / Address**
- **Industry:** real estate development | event planning and production | other industry (say which)
- **Location type:** NYC-based | remote
- **Size** (number and source) and **years in business**
- **What they do** (1 line, in their own terms)
- **Why I fit** (cite the specific fact from my background)
- **Why they would want me** (the value I bring)
- **Evidence of legitimacy** (projects, events, team, years; link each)
- **Fit score 0-100** (never 100; 0 if you cannot verify what they do)
- **Best contact** (a named person and role found on their site; if none, "not found". Never guess an email address.)
- **Suggested first move** (1 sentence)
- **Sources** (links)

### 2. Gemini API Structured JSON Schema (For programmatic API execution)
When responding via Gemini API in JSON mode (`responseMimeType: "application/json"`), generate 3 distinct target companies and return a single valid JSON object containing an array of 3 company objects:
```json
{
  "companies": [
    {
      "company": "Company Name",
      "website": "https://company-domain.com",
      "address": "Street address or neighborhood, NYC",
      "locationType": "NYC-based",
      "industry": "real estate development",
      "size": "15-25 employees (verified via LinkedIn / Team page)",
      "yearsInBusiness": 8,
      "whatTheyDo": "One crisp line describing what the company does in their own terms.",
      "targetRoleTitle": "Sales & Leasing / Investor Relations Lead",
      "whyFit": "Cite exact background fact (Rushable/Edward Jones/JPMorgan, sales/finance, hospitality).",
      "whyTheyWantMe": "Specific growth need Max can fill and immediate value brought.",
      "legitimacyEvidence": "Named past developments or corporate events with verifiable track record.",
      "fitScore": 88,
      "contacts": [
        {
          "name": "Founder or Principal Name",
          "role": "Managing Principal / Founder",
          "email": "",
          "phone": ""
        }
      ],
      "suggestedFirstMove": "Concise outreach hook citing a specific project or shared connection.",
      "sources": [
        "https://company-domain.com",
        "https://linkedin.com/company/..."
      ],
      "unverifiedItems": [
        "Internal team structure details to clarify"
      ],
      "firstCallQuestions": [
        "Are they currently handling sales and leasing in-house or through external brokers?"
      ]
    }
  ]
}
```

## RULES
- Every claim needs a source link. If you cannot verify it, write "unverified".
- Never invent companies, people, emails, phone numbers, project sizes or numbers.
- Do not claim I have experience that is not listed above.
- Flag anything that looks like a scam or high-pressure recruiting.
- End with a short list of what you could not verify and what to ask the company on a first call.
- Do not output placeholders like `[Insert Name]` or fake emails like `info@company.com`; leave unverified contact fields blank if not publicly published.
