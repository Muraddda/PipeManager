# V2 Architecture (Architect)

## Goal
Keep V1's two-state UX (board, then a cockpit drawer) and its build plan, but retarget it to Max's real background and make it trustworthy: nothing invented, nothing lost.

## Decisions

| Decision | Why |
|---|---|
| Resume facts live in one file, `candidate.py` | Matching, stories and email drafts all read it, so a claim can't appear in one place and not another. |
| Match engine is deterministic keyword evidence, not a model | It can't hallucinate. Each hit shows the resume line behind it; each gap shows a mitigation. |
| Seeded roles are unscored until a real posting is analyzed | I wrote the template text from the resume, so scoring it would be circular. |
| Drafts are built server-side from verified story "pitches" | Facts stay out of JavaScript. Unknown details are `[bracketed]` blanks the UI warns about. |
| All edits persist through one `api()` helper | V1 lost most edits on reload. Failed saves now show an error and a "Not saved" status. |
| Contact details in gitignored `profile.local.json` | The repo can be shared without exposing email or phone. |
| Server binds 127.0.0.1, no CORS, requires JSON content type and a localhost Host header | A local tool that listens on all interfaces with `CORS: *` can be driven by any website you visit. |

## Layout

```
Browser (index.html: vanilla JS, Tailwind + Lucide pinned)
   │ REST (JSON)
server.py   routing table, validation, localhost guards
   ├─ matcher.py   score + evidence + gaps + story picks
   ├─ drafts.py    four email templates
   ├─ linter.py    anti-slop rules (single copy)
   ├─ candidate.py verified skills, gaps, STAR stories
   └─ db.py        SQLite (WAL, FK on, indexed) ← seed.py
```

## API
`GET /api/opportunities` · `GET /api/profile` · `POST /api/opportunities` · `PATCH|DELETE /api/opportunities/<id>` · `POST /api/opportunities/reorder` · `POST /api/opportunities/<id>/{notes,tasks,comms,analyze}` · `PATCH|DELETE /api/tasks/<id>` · `POST /api/ai/{draft,anti-slop-linter}`

Writes return 404 for unknown ids, 400 for bad input (stage names, JSON, types), 409 for duplicate ids, 415 for non-JSON bodies.

## Changed from V1
Stage "Technical Interview" is now "Interview Loop". `title` holds the role only; company is its own editable field. Hard-coded copy ("Verified 96% match", "100% Anti-Slop Verified", "payments API idempotency") is gone. Dead browser buttons are removed.
