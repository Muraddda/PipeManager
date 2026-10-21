# Optimization notes (Optimizer)

Measured, not assumed. Scripts: `python3 tests/bench.py 500`; render time measured in the browser with 500 cards.

| Area | Result |
|---|---|
| Read path, 500 roles × (3 notes + 3 tasks) | ~21 ms list + serialize (5 queries, no N+1). Payload 2.2 MB with 1.5 KB job text per role; irrelevant over loopback, gzip was originally skipped, then added for the Tailscale use case (see Transport). |
| Board render, 500 cards | ~23 ms full render; ~4 ms when a filter is active. One delegated listener; no per-card handlers. |
| Writes | Field edits are coalesced per role (400 ms), so typing sends one PATCH instead of one per keystroke. Flushed on close, switch and page hide. |
| SQLite | WAL mode, foreign keys on, indexes on every child `opportunity_id` and on `order_index`. Connections roll back on error. |
| Linter / drafts | Linter debounced 250 ms; stale responses discarded. Regexes compiled once at import. |
| Transport | gzip on responses >= 1 KB when the client asks (board payload 2.2 MB -> 33 KB, ~9 ms to compress); HTTP/1.1 keep-alive so a session reuses one connection. Matters over Tailscale; error responses close the connection because their request body may be unread. |
| Board render, repeated triggers | `renderBoard()` now coalesces into one `requestAnimationFrame` pass and buckets cards by stage in one loop (was filter+sort of every role per column). Typing in the search box or company/title/value fields no longer rebuilds the board per keystroke; column scroll positions survive a redraw. 10 rapid search keystrokes at 500 cards: ~780 ms -> ~270 ms in headless Chromium. |
| Icons | `lucide.createIcons()` coalesced to one scan per event (kept from V1 refactor). |

## Considered and skipped
- Virtual scrolling, caching headers for the API: no measurable win at personal-pipeline scale (tens to low hundreds of roles).
- A job queue or async server: requests complete in single-digit milliseconds.
