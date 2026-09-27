# Submission checklist — Mirage (GIBC V2, Track 02 Applied/Finance)

## Devpost / GIBC requirements

| Requirement | Where satisfied | Status |
|---|---|---|
| Project name, tagline ≤ 60 chars | Mirage — "The backtest lie detector." (26) | done |
| Full description (Inspiration … What's next) | `submission/DEVPOST.md` | done |
| Built With tag list | `submission/DEVPOST.md` → "Built With" | done |
| Hosted demo video, 2–5 min | `submission/mirage_demo.mp4` (3:03, 1920×1080, h264 + AAC narration, burned English subtitles) | file done; **YouTube upload pending (human)** |
| ≥ 3 screenshots | `submission/screenshots/` (9 UI PNGs) + `reports/figures/` | done |
| Public repo | https://github.com/sharonbasovich/mirage (public, exists) | `main` and [`codex/gibc-worldbank-audit`](https://github.com/sharonbasovich/mirage/tree/codex/gibc-worldbank-audit) include the audited source and committed E2/E4 result JSON |
| Live/deployed project | Optional public demo; rules require a working prototype and hosted video | Devin built-in deploy approval pending; no live URL yet |

## Human TODO before submit

- [x] Push the audited source and reproducible E2/E4 results to `main`
- [ ] Optional: approve the Devin deploy, smoke-test it, and add its URL
- [ ] Upload `mirage_demo.mp4` to YouTube, Vimeo, or Youku (unlisted ok), paste link into Devpost
- [ ] Submit on Devpost before **Oct 1 2026, 15:45 UTC** (not yet submitted)

## Track 02 rules / constraints

| Rule | Where satisfied |
|---|---|
| No paid keys/services; product is pure stats/ML | numpy/scipy/pandas/sklearn only; no LLM in product; free keyless data |
| Public data, source + license cited | Bundled World Bank Pink Sheet (CC BY 4.0) with attribution in README "Data", `data/worldbank/README.md`, DEVPOST. Yahoo data is optional, user-local only, under Yahoo's terms, not redistributed, and not used in the submitted demo/video/figures |
| Historical simulation only; not-financial-advice disclaimer | README top + DEVPOST bottom |
| AI disclosure | README + DEVPOST "AI assistance disclosure"; "Devin" in Built With |
| English everything | all docs/code/video |
| Team credit | Sharon Basovich (solo) in README "Team" and LICENSE |
| Rigor & validation | Submitted evidence: E2 synthetic power/ROC + label confusion matrix and E4 World Bank report cards (hypothetical price-series backtests; DSR shown as a confidence estimate, not a p-value). Optional local E1/E3 (Yahoo) are outside the submission; 54 tests incl. PBO≈0.5-on-noise, PSR/MinTRL units, no-lookahead, ledger tamper, API abuse regressions |
| Innovation & impact | Trial Ledger (hash chain; detects edits within an intact ledger, unsigned); upload-audit for other backtesters |
| Technical feasibility | single-command run; Docker; CI; bounded public API; ~10-min seeded experiments |
