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

## 2026-09-25 — QA round 2 (statistical correctness)
- Fixed PSR/MinBTL per-period unit bug (Bailey & LdP formulas take per-period SR).
- CSCV IS/OOS Sharpes now annualized; verdict degradation uses median CSCV IS-vs-OOS.
- Reality Check added as a verdict component (0.20); rc_p>0.5 hard-caps label at Unclear.
- Cost-fragility capped breakeven renders as ">300 bps (never crosses)".
- E1: 0/20 zero-skill zoos Survives (16 Mirage/4 Unclear); DSR alone misses 45%.
- E2 at T=2500: verdict Survives 53/82/98% at planted SR 1.0/1.5/2.0; label
  confusion TP102/FP5/FN53/TN160 = 82% accuracy.
- E3: only tsmom_btc Survives (95.0); rsi/ml capped to Unclear by RC gate.
- Demo video re-rendered: 2:41 with Piper TTS narration (AAC) + burned subs.
