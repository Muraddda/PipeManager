# Review findings (Reviewer)

Checked against V1 (`Claude/job_hunt_pipeline`) and the new code. 30 tests in `tests/test_v2.py` cover each item marked **tested**.

## Fixed in V2

| # | Severity | Finding | Status |
|---|---|---|---|
| R1 | High | Seed data described a fictional software engineer: fake contacts, a fake $290K offer, invented GitHub/Loom links. Emailing these would misstate the candidate. | Replaced with resume-derived data; **tested** (no invented people, comms or history). |
| R2 | High | Most UI edits (stage, comp, contacts, notes, tasks, comms, new roles) never reached the server and vanished on reload. | All writes persisted; **tested** end to end. |
| R3 | High | `run.sh` deleted the database on every start. | `init_db` keeps data; `db.py --reset` is explicit; **tested**. |
| R4 | High | Server listened on all interfaces with `Access-Control-Allow-Origin: *` and accepted any content type, so any web page could read or delete data (including `text/plain` cross-site POSTs and DNS rebinding). | Bind 127.0.0.1, no CORS, JSON-only (415), Host check (403); **tested**. |
| R5 | Medium | Email recipient was guessed (`first.last@company.com`). | Never guessed; blank until you enter it; **tested**. |
| R6 | Medium | `href` built from stored URLs allowed `javascript:` links. | `safeUrl()` allows http(s) only. |
| R7 | Medium | Writes to unknown ids returned success; invalid stages and non-boolean flags were stored. | Return 404 / 400; **tested**. |
| R8 | Medium | Reordering saved only one of the two swapped cards. | Both saved. |
| R9 | Low | Race: a slow draft or lint response could overwrite a newer one. | Token guard on both. |
| R10 | Low | Editing the company field wiped an unanalyzed pasted posting. | Browser panel no longer re-rendered on that edit (caught while reviewing). |
| R11 | Low | Delete had no confirmation; unpinned Tailwind CDN. | Confirm dialog; pinned 3.4.17 (Lucide 0.469.0). |
| R12 | Low | Story text inferred motives ("you wanted to run your own business"). | Reworded to resume facts only. |

## Known limits (not fixed)
- The matcher is keyword-based. It can miss synonyms and can't judge seniority or context. Treat the score as a prompt to read the gaps, not a verdict.
- "Years of experience" is hard-coded to 6 (since May 2020). Update `candidate.YEARS_CLIENT_FACING` as time passes.
- Placeholder comp ($150K) and role templates are not market data.
- UI behavior was verified by scripted interaction in the in-app browser, not by an automated UI test suite.
- Opening a draft in Gmail relies on the browser allowing the new tab.
