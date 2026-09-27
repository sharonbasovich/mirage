# PROGRESS

## Status (2026-09-27)
- Public repo https://github.com/sharonbasovich/mirage: `main` is at `69290c5`.
  The hardening commit `1206247` is published on the review branch
  https://github.com/sharonbasovich/mirage/tree/codex/gibc-worldbank-audit.
  The follow-up submission-audit commit on top of it ships as a git bundle
  (this org's Devin git proxy returns 403 on push).
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
- Submitted evidence: E2 (synthetic) + E4 (bundled World Bank, CC BY 4.0, hypothetical price-series backtests). E1/E3 remain optional local Yahoo experiments outside the submission
- FastAPI + React app, CLI, Docker, CI
- API hardening: bounded grids/params/symbols, bounded uploads (bytes/rows/
  cols), declared-trial cap, concurrency cap (429), server-generated program
  IDs + path confinement, same-origin CORS (env allowlist), generic 500s,
  SPA path confinement, analysis retention cap
- Data rights: Yahoo CSVs removed from the tree (user-local fetch cache);
  bundled World Bank Pink Sheet subset with attribution
- Video rebuilt on E2/E4 only, with narration + burned subtitles; 9 screenshots; submission kit
- DSR/PSR labelled as confidence (exceedance) estimates, not p-values; RC p > 0.5 described as insufficient evidence of outperformance

## Pending (human)
- [ ] Push the submission-audit bundle commit onto `codex/gibc-worldbank-audit`, review, merge to main
- [ ] Approve deploy, then smoke-test and insert the URL
- [ ] YouTube upload, Devpost submission
- [ ] Optional: purge the old Yahoo CSVs from git history (history rewrite + force push; human decision)
