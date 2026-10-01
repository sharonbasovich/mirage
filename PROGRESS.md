# PROGRESS

## Status (2026-10-01)
- Public repo https://github.com/sharonbasovich/mirage: `main` and the
  review branch `codex/gibc-worldbank-audit` include the audited source and
  reproducible result files through `5a75fcf`. The Devin
  hardening and submission-audit commits were imported from verified Git
  bundles and pushed after independent QA.
- Tests: 56 passing (33 core + 21 API abuse regressions + 2 deploy-entrypoint
  regressions); ruff, mypy, tsc clean.
- Deploy: **no public app was deployed**. Devin's built-in free backend deploy
  was approved and retried but failed at app detection on every attempt with
  "Check that the project has a pyproject.toml and a FastAPI app", even though
  the documented requirements are met (`pyproject.toml` with a project name +
  a FastAPI app named `app` in `app/main.py`). The project serves locally via
  `uvicorn app.main:app`; no live URL exists.
- Devpost: **submitted and live** — https://devpost.com/software/mirage-1vh78d
- Demo video: hosted at https://www.youtube.com/watch?v=Q3b8egv8syM

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
- [x] Attempt the free Devin backend deploy — approved and retried; failed at
  app detection (platform-side check rejects a valid FastAPI project). No
  public live URL; the rules require a running prototype and hosted video,
  not a public live-app URL.
- [x] Host the 3:03 demo on YouTube — https://www.youtube.com/watch?v=Q3b8egv8syM
- [x] Submit the Devpost entry — https://devpost.com/software/mirage-1vh78d
- [ ] Optional: purge the old Yahoo CSVs from git history (history rewrite + force push; human decision)
