# PROGRESS

## Status (2026-09-27)
- Public repo https://github.com/sharonbasovich/mirage exists at `69290c5`.
  This org's Devin git proxy returns 403 on push, so the security/data-rights
  hardening commit ships as a git bundle and patch for the human to push.
- Tests: 54 passing (33 core + 21 API abuse regressions); ruff, mypy, tsc clean.
- Deploy: Devin built-in backend deploy (free) is **pending approval**. No live
  URL yet.
- Devpost: **not submitted**. YouTube upload is still pending (human).

## Done
- Diagnostics (PSR/DSR/MinTRL per-period units, CSCV/PBO, purged CV, Reality
  Check, cost fragility, haircuts) and a transparent verdict with an RC gate
- Backtester (daily or monthly bars), strategy library, ML with purged walk-forward
- Hash-chained Trial Ledger + unsigned certificate. The docs state it detects
  edits within an intact ledger, not a full rewrite
- Experiments E1–E3 (E1/E3 on user-fetched Yahoo data) + E4 (bundled World Bank, CC BY 4.0)
- FastAPI + React app, CLI, Docker, CI
- API hardening: bounded grids/params/symbols, bounded uploads (bytes/rows/
  cols), declared-trial cap, concurrency cap (429), server-generated program
  IDs + path confinement, same-origin CORS (env allowlist), generic 500s,
  SPA path confinement, analysis retention cap
- Data rights: Yahoo CSVs removed from the tree (user-local fetch cache);
  bundled World Bank Pink Sheet subset with attribution
- Video 2:31 with narration + burned subtitles; 8 screenshots; submission kit

## Pending (human)
- [ ] Push hardening bundle/patch
- [ ] Approve deploy, then smoke-test and insert the URL
- [ ] YouTube upload, Devpost submission
- [ ] Optional: purge the old Yahoo CSVs from git history (history rewrite + force push; human decision)
