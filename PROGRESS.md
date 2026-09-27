# PROGRESS

## Status (2026-09-27)
- Public repo https://github.com/sharonbasovich/mirage: `main` and the
  review branch `codex/gibc-worldbank-audit` include the audited source and
  reproducible result files through `5a75fcf`. The Devin
  hardening and submission-audit commits were imported from verified Git
  bundles and pushed after independent QA.
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
- Submitted evidence: committed `reports/e2.json` (synthetic) and
  `reports/e4.json` (bundled World Bank, CC BY 4.0, hypothetical price-series
  backtests). E1/E3 remain optional local Yahoo experiments outside the submission
- FastAPI + React app, CLI, Docker, CI
- API hardening: bounded grids/params/symbols, bounded uploads (bytes/rows/
  cols), declared-trial cap, concurrency cap (429), server-generated program
  IDs + path confinement, same-origin CORS (env allowlist), generic 500s,
  SPA path confinement, analysis retention cap
- Data rights: Yahoo CSVs removed from the tree (user-local fetch cache);
  bundled World Bank Pink Sheet subset with attribution
- Video rebuilt on E2/E4 only, with narration + burned subtitles; 9 screenshots; submission kit
- DSR/PSR labelled as confidence (exceedance) estimates, not p-values; RC p > 0.5 described as insufficient evidence of outperformance

## Pending
- [ ] Optional: approve deploy, smoke-test, and insert the URL if a live demo
  would help judges; the rules require a running prototype and hosted video,
  not a public live-app URL
- [ ] Host the 3:03 demo on YouTube, Vimeo, or Youku (unlisted is permitted)
- [ ] Complete and finally submit the Devpost entry before the deadline
- [ ] Optional: purge the old Yahoo CSVs from git history (history rewrite + force push; human decision)
