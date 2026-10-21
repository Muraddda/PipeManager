# Optimization notes (Optimizer)

Measured, not assumed. Scripts: `python3 tests/bench.py 500`; render time measured in the browser with 500 cards.

| Area | Result |
|---|---|
| Read path, 500 roles × (3 notes + 3 tasks) | ~21 ms list + serialize (5 queries, no N+1). Payload 2.2 MB with 1.5 KB job text per role; irrelevant over loopback, so gzip was **not** added. |
| Board render, 500 cards | ~23 ms full render; ~4 ms when a filter is active. One delegated listener; no per-card handlers. |
| Writes | Field edits are coalesced per role (400 ms), so typing sends one PATCH instead of one per keystroke. Flushed on close, switch and page hide. |
| SQLite | WAL mode, foreign keys on, indexes on every child `opportunity_id` and on `order_index`. Connections roll back on error. |
| Linter / drafts | Linter debounced 250 ms; stale responses discarded. Regexes compiled once at import. |
| Icons | `lucide.createIcons()` coalesced to one scan per event (kept from V1 refactor). |

## Considered and skipped
- Virtual scrolling, gzip, caching headers for the API: no measurable win at personal-pipeline scale (tens to low hundreds of roles).
- A job queue or async server: requests complete in single-digit milliseconds.
