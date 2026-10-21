# Job Hunt Pipeline Studio V2

A local job-search cockpit built around one candidate: **Max Mardan**, a sales and finance professional (Rushable, Edward Jones, JPMorgan, two restaurants founded and sold). V1 was a generic software-engineer demo. V2 is built from the resume.

## What it does

- **Kanban board** of target roles across five stages, with reorder, search and stage filter.
- **Truth-constrained match engine** (`matcher.py`). Paste a real job posting and it scores the role against facts in `candidate.py`. Every strength cites the resume line behind it. Every gap comes with an honest answer. A score is never 100%, and a posting that mentions nothing it recognizes gets no score.
- **STAR story bank**: six stories built only from resume facts, each with prompts for details only you know. The matcher picks which to lead with.
- **Gmail Studio**: four drafts (hiring-manager note, screening follow-up, post-interview thank-you, offer negotiation) written from your verified stories. It never guesses an email address, flags `[bracketed]` blanks you still need to fill, and opens Gmail compose. Nothing is sent from the app.
- **Anti-slop linter**: flags stock phrases ("spearheaded", "passionate about", "proven track record") and suggests plain wording.
- **Everything saves** to SQLite as you type. Restarting keeps your data.

## Run it

```bash
./run.sh            # http://localhost:8000
python3 db.py --reset   # wipe and reseed the demo data
python3 -m unittest discover -s tests -v   # 30 tests, no dependencies
```

Needs Python 3 only. The UI loads Tailwind and Lucide from a CDN (versions pinned).

## Make it yours

- Copy `profile.local.example.json` to `profile.local.json` and set your email. That file is gitignored, so contact details never reach the repo.
- Seeded roles (Toast, Block/Square, Ramp, Brex, Stripe) are **targets with template job text**, so they start UNSCORED. Paste each real posting and press Analyze. Target comp is a $150K placeholder; edit it.
- Edit `candidate.py` to add stories or skills. Keep to facts you can defend in an interview.

## Docs

- [Architecture](docs/ARCHITECTURE.md) · [Review findings](docs/REVIEW.md) · [Optimization notes](docs/OPTIMIZATION.md) · [Original build plan](docs/BUILD_PLAN.md)
