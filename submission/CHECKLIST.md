# Submission checklist — Mirage (GIBC V2, Track 02 Applied/Finance)

## Devpost / GIBC requirements

| Requirement | Where satisfied | Status |
|---|---|---|
| Project name, tagline ≤ 60 chars | Mirage — "The backtest lie detector." (26) | done |
| Full description (Inspiration … What's next) | `submission/DEVPOST.md` | done |
| Built With tag list | `submission/DEVPOST.md` → "Built With" | done |
| Hosted demo video, 2–5 min | `submission/mirage_demo.mp4` (3:03, 1920×1080, h264 + AAC narration, burned English subtitles) | file done; **YouTube upload pending (human)** |
| ≥ 3 screenshots | `submission/screenshots/` (9 UI PNGs) + `reports/figures/` | done |
| Public repo | https://github.com/sharonbasovich/mirage (public, exists) | `main` at `69290c5`; hardening `1206247` on review branch [`codex/gibc-worldbank-audit`](https://github.com/sharonbasovich/mirage/tree/codex/gibc-worldbank-audit); submission-audit follow-up delivered as bundle, **push + merge pending (human)** |
| Live/deployed project | Devin built-in backend deploy (free) | **approval pending**; URL goes into README/DEVPOST after smoke test |

## Human TODO before submit

- [ ] Push the submission-audit bundle commit onto `codex/gibc-worldbank-audit`, review, merge to `main`
- [ ] Approve the Devin deploy (built-in, free) in the Devin session
- [ ] After smoke test (Strategy Lab → Verdict → Ledger → certificate), paste deployed URL into README + DEVPOST "Try it out"
- [ ] Upload `mirage_demo.mp4` to YouTube (unlisted ok), paste link into Devpost
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
