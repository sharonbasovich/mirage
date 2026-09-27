# Submission checklist — Mirage (GIBC V2, Track 02 Applied/Finance)

## Devpost requirements

| Requirement | Where satisfied |
|---|---|
| Project name | Mirage |
| Tagline ≤ 60 chars | "The backtest lie detector." (26) |
| Full description (Inspiration / What it does / How we built it / Challenges / Accomplishments / What we learned / What's next) | `submission/DEVPOST.md` |
| Built With tag list | `submission/DEVPOST.md` → "Built With" |
| Demo video 2–5 min MP4 1920×1080, English subtitles | `submission/mirage_demo.mp4` + burned SRT (`submission/mirage.srt`) |
| Public repo runnable by a judge | repo + README quickstart (`pip install -e . && pytest && uvicorn` or `docker compose up`); data committed → offline |
| Live/deployed project | deployed FastAPI URL (see DEVPOST.md "Try it out") |
| Screenshots | `submission/screenshots/` (≥5 UI PNGs + experiment figures) |

## Human TODO before submit

- [ ] Create public GitHub repo `sharonbasovich/mirage` and push (or untar `mirage-source.tar.gz`)
- [ ] Approve the Devin deploy (built-in, free) in the Devin session
- [ ] Paste deployed URL + repo URL into DEVPOST.md "Try it out"
- [ ] Upload `mirage_demo.mp4` to YouTube (unlisted ok), paste link into Devpost
- [ ] Fill Terry's name/handle if applicable
- [ ] Submit on Devpost before **Oct 1 2026, 15:45 UTC**

## Track 02 rules / constraints

| Rule | Where satisfied |
|---|---|
| No paid keys/services; product is pure stats/ML | numpy/scipy/pandas/sklearn only; no LLM in product; yfinance (free, keyless) |
| Public data only, source + license cited | README "Data" + DEVPOST "Data & citations" |
| Historical simulation only; not financial advice disclaimer | README top + DEVPOST bottom |
| AI disclosure mandatory | README + DEVPOST "AI assistance disclosure"; "Devin" in Built With |
| English everything | all docs/code/video |
| Team credit + Terry placeholder | README "Team", LICENSE |
| Rigor & validation | E1 FPR, E2 power/ROC, E3 report cards; `make experiments` reproduces all figures; 29 unit tests incl. PBO≈0.5-on-noise, DSR bounds, no-lookahead, ledger tamper |
| Innovation & impact | Trial Ledger (pre-registration for backtests); upload-audit audits other backtesters' output |
| Technical feasibility | single-command run; Docker; CI; ~10-min seeded experiments |

## Human TODO before submit

- [ ] Create public GitHub repo `sharonbasovich/mirage` and push (or untar `mirage-source.tar.gz`)
- [ ] Approve the Devin deploy (built-in, free) in the Devin session
- [ ] Paste deployed URL + repo URL into DEVPOST.md "Try it out"
- [ ] Upload `mirage_demo.mp4` to YouTube (unlisted ok), paste link into Devpost
- [ ] Fill Terry's name/handle if applicable
- [ ] Submit on Devpost before **Oct 1 2026, 15:45 UTC**
