# PROGRESS

## Done
- [x] Repo scaffold (pyproject, pinned deps, ruff/mypy/pytest config)
- [x] Data cache: 18 symbols via yfinance, committed CSVs + data hash
- [x] Vectorized no-lookahead backtester (costs, slippage, vol targeting)
- [x] Strategy library: ma_cross, tsmom, sector_mom (12-1 top-k), rsi_rev,
      bollinger, buy_hold, ml_daily (purged walk-forward + embargo)
- [x] SQLite hash-chained Trial Ledger + pre-registration certificate export
- [x] Diagnostics: Sharpe/PSR, DSR + MinBTL, PBO via CSCV (S=16), purged CV,
      stationary-bootstrap Reality Check, cost fragility, B/Holm/BHY haircuts,
      Mirage Score verdict
- [x] 29 unit tests — all pass (ruff + mypy clean)
- [x] Experiments E1 (FPR), E2 (power/ROC), E3 (real report cards) → reports/
- [x] FastAPI backend + React/TS/Tailwind/Recharts frontend (single origin)
- [x] CLI: mirage run / audit / report / programs / experiments
- [x] Dockerfile + docker-compose.yml + GitHub Actions CI
- [x] README (disclaimer, AI disclosure, setup, reproduce-figures, citations),
      LICENSE (MIT), submission kit (DEVPOST.md, VIDEO_SCRIPT.md, CHECKLIST.md)
- [x] Demo video submission/mirage_demo.mp4 (2:34, 1920x1080, burned subs)
      + submission/mirage.srt
- [x] 8 UI screenshots + 6 experiment figures
- [x] Pre-registration certificate for demo program
- [x] Clean-clone QA: pip install → 29/29 tests → app serves

## Pending / blocked
- [ ] **GitHub repo creation** — push to sharonbasovich/mirage returns 403:
      repo does not exist upstream and this environment has no GitHub API token.
      Needs the human to create an empty public repo `sharonbasovich/mirage`;
      fallback `mirage-source.tar.gz` attached in the Devin session.
- [ ] **Deploy approval** — `deploy backend` awaits the human's approve click
      in the Devin session.
- [ ] YouTube upload + Devpost form fill (human-only actions)

## Working style notes
- Local repo has full history; commit early and often.
- Everything runs offline; `make experiments` re-derives all figures.
