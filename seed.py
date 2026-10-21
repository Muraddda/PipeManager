"""First-run seed: target roles that fit Max's background, scored by the matcher.

No contacts, offers, dates or application history are invented. Job text is a
template describing the role type, so seeded roles stay unscored (0) until the real
posting is pasted and analyzed. Evidence and story picks still come from the matcher.
Target comp is an editable placeholder.
"""

import candidate
import matcher

# (id, company, title, location, careers page, team, template requirements)
_TARGETS = [
    ("job-1", "Toast", "Account Executive, Restaurants", "New York, NY",
     "https://careers.toasttab.com", "Restaurant Sales",
     "Full-cycle sales to restaurants and small business owners. Outbound prospecting, demos, closing new business against quota. Restaurant and hospitality experience, payments and fintech familiarity, Salesforce."),
    ("job-2", "Block (Square)", "Small Business Account Executive", "New York, NY",
     "https://block.xyz/careers", "Seller SMB Sales",
     "Prospecting and closing small business merchants. Consultative discovery, demos, quota, CRM pipeline management. Payments, lending and financial services knowledge, small business owners, Salesforce."),
    ("job-3", "Ramp", "Mid-Market Account Executive", "New York, NY",
     "https://ramp.com/careers", "Mid-Market Sales",
     "Full-cycle B2B sales to finance leaders. Outbound prospecting, consultative discovery, demos, quota, pipeline forecasting. Fintech, corporate cards, treasury and credit. 4+ years of sales experience, SaaS, Salesforce."),
    ("job-4", "Brex", "Account Executive, Commercial", "New York, NY",
     "https://www.brex.com/careers", "Commercial Sales",
     "Own the full sales cycle with startups and growth companies. Outbound prospecting, discovery, demos, close new business against quota. Fintech, credit, banking, stakeholder relationships, SaaS, CRM."),
    ("job-5", "Stripe", "Account Executive, Startups", "New York, NY",
     "https://stripe.com/jobs", "Startup Sales",
     "Build pipeline and close new business with startups. Outbound prospecting, consultative selling, demos, quota. Payments and financial services, go-to-market, cross-functional partnership, API and developer familiarity, Salesforce, 5+ years of experience."),
]

_ADDED = "Today"


def _build():
    opps, notes, tasks = [], [], []
    for idx, (opp_id, company, title, location, url, team, text) in enumerate(_TARGETS):
        result = matcher.analyze(text, basis="template")
        opps.append({
            "id": opp_id,
            "title": title,
            "company": company,
            "location": location,
            "stage_id": "wishlist",
            "value": candidate.DEFAULT_TARGET_OTE,
            "contact_name": "",
            "contact_email": "",
            "contact_role": "Recruiter",
            "hiring_manager_name": "",
            "hiring_manager_email": "",
            "job_url": url,
            "order_index": 1000 * (idx + 1),
            "match_score": 0,  # unscored until a real posting is analyzed
            "match_analysis_json": {k: result[k] for k in ("basis", "strengths", "gaps", "matched", "stories")},
            "proof_of_work_json": {
                "artifactName": f"30-60-90 Day Plan: {title}",
                "artifactType": "One-page plan",
                "status": "planned",
                "artifactUrl": "",
            },
            "job_details_json": {
                "team": team,
                "requirements": text,
                "techStack": "",
                "compensation": "Set from the posting",
                "isTemplate": True,
            },
        })
        for n, story_id in enumerate(result["stories"][:2], start=1):
            story = candidate.story_by_id(story_id)
            notes.append((f"n-{opp_id}-{n}", opp_id, "star_story", f"STAR: {story['title']}",
                          candidate.story_text(story), _ADDED))
        for n, (title_t, cat) in enumerate([
            (f"Find the {company} hiring manager (sales director or VP) and add them here", "outreach"),
            ("Paste the real job posting into Match & Gaps and re-analyze", "prep"),
            (f"Draft the 30-60-90 day plan for {company}", "artifact"),
            (f"Look for a warm referral into {company}", "referral"),
        ], start=1):
            tasks.append((f"t-{opp_id}-{n}", opp_id, title_t, cat, 0, None))
    return opps, notes, tasks


SEED_OPPORTUNITIES, SEED_NOTES, SEED_TASKS = _build()
SEED_COMMS = []
SEED_FILES = []
