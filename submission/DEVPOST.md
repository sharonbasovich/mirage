# Devpost submission — Mirage

> Fill the bracketed placeholders, then paste each section into Devpost.

**Project name:** Mirage

**Tagline (≤60 chars):** The backtest lie detector.

**Elevator pitch:** Try enough parameter combinations and the best backtest
is partly luck. Mirage records every trial in a hash-chained ledger and runs
the academic overfitting battery (DSR, PBO, purged CV, Reality Check) to show,
in plain English, how much of a backtest survives selection-bias checks.

---

## Inspiration

A reported backtest Sharpe is usually the *best of N tries*, and N is rarely
reported. Clinical trials handle the same problem with pre-registration and
multiple-testing corrections. Quantitative finance has the math (Bailey &
López de Prado; White's Reality Check; Harvey–Liu haircuts) but little tooling
a student or retail researcher can use. Mirage makes "did my parameter search
overfit?" a one-click question and keeps the trial count in a recorded ledger.

## What it does

- **Backtester:** vectorized engine for daily or monthly bars with strict
  no-lookahead (signal at close of bar *t* → position from bar *t+1*), costs
  and slippage in bps, optional volatility targeting. Strategy library: MA
  crossover, time-series momentum, 12-1 cross-sectional momentum, RSI and
  Bollinger mean reversion, buy-and-hold, and a gradient-boosted ML classifier
  trained with purged walk-forward CV + embargo.
- **Trial Ledger:** every trial (UI, CLI, or API) appends to a SQLite
  hash-chained ledger, where each entry's hash includes the previous entry's,
  and the Deflated Sharpe Ratio uses that recorded count. The chain detects
  edits or deletions only within an intact ledger. It is **neither signed nor
  externally anchored**, so someone with write access who rewrites the whole
  database and recomputes the hashes cannot be caught from the file alone.
  Mirage exports an **unsigned** certificate JSON (trial count, best trial,
  chain head, verdict) per program.
- **Diagnostics battery:** Deflated Sharpe Ratio (Bailey & López de Prado
  2014), Probability of Backtest Overfitting via CSCV (Bailey, Borwein, López
  de Prado & Zhu 2017), purged CV, stationary-bootstrap Reality Check (White
  2000), cost-fragility breakeven, minimum backtest length, and
  Bonferroni/Holm/BHY haircuts (Harvey & Liu 2015).
- **Verdict card:** a transparent 0–100 Mirage Score with the component table
  always visible, plus rule-generated plain-English sentences (no LLM). The DSR
  is reported as a *confidence (exceedance) estimate* that the true Sharpe
  exceeds the best-of-N luck threshold; it is not a p-value and not the
  probability that genuine skill exists. A large Reality Check p-value is
  reported as insufficient evidence of outperformance, not proof of no edge.
- **Upload-audit:** upload a returns CSV from another backtester plus a
  declared trial count and get the same verdict.
- **Self-validation:** detector error rates (ROC/AUC, detection power, label
  accuracy) measured on synthetic strategies with known zero or planted skill.

## How we built it

Pure statistics, no LLM in the product. Python (numpy/pandas/scipy/
scikit-learn) core package; FastAPI backend serving a React + TypeScript +
Tailwind + Recharts single-origin app; SQLite ledger; typer CLI; matplotlib
figures; pytest + ruff + mypy; Docker; GitHub Actions CI.

DSR deflates the best Sharpe by the expected maximum under luck given the
*variance of trial Sharpes*; PSR/DSR/MinTRL work in per-period units
internally. CSCV partitions the returns matrix into S=16 blocks over all
C(16,8)=12,870 combinations and measures P(λ<0) of the rank logits. The
Reality Check uses a Politis–Romano stationary bootstrap of benchmark-excess
returns.

## Submitted evidence

The submitted demo, video and figures use only two sources: bundled World
Bank Pink Sheet data (CC BY 4.0) and synthetic series.

**E4: World Bank Pink Sheet, four zoos** (`reports/e4.json`, 1971-01 →
2026-08, 668 monthly observations; benchmark = buy-and-hold of the program's
own assets). These are *hypothetical price-series backtests*: Pink Sheet
values are monthly reference/spot prices, not an investable return series or
executable bars. The results illustrate the diagnostics and are not realizable
trading P&L. Futures roll, storage, financing and execution details are not
modeled.

| Program | Trials | Best IS Sharpe | DSR confidence | PBO | RC p | Score | Verdict |
|---|---|---|---|---|---|---|---|
| MA crossover, gold | 12 | 0.71 | 1.000 | 0.23 | 0.59 | 81.2 | Unclear |
| TS momentum, Brent | 10 | 0.62 | 1.000 | 0.01 | 0.52 | 87.4 | Unclear |
| Cross-sectional momentum, 8 commodities | 12 | 0.34 | 0.967 | 0.27 | 0.99 | 68.7 | Unclear |
| RSI mean reversion, gold | 27 | 0.23 | 0.467 | 0.30 | 1.00 | 51.8 | Unclear |

Gold trend-following and Brent momentum pass DSR and PBO, but the Reality
Check finds insufficient evidence that either outperforms buy-and-hold after
data snooping (RC p > 0.5), so Mirage caps both at Unclear.

**E2: synthetic planted skill** (`reports/e2.json`; 8 skill levels × 40 reps
× 50 strategies, T = 2,500). One strategy per zoo gets a planted true Sharpe
from 0 to 2.0.
- ROC AUC for "the in-sample winner has true skill": **DSR 0.914, PBO 0.900**.
- Verdict label on ground truth (Survives = positive): TP 102 / FP 5 / FN 53 /
  TN 160, **81.9% accuracy**.
- Pure-noise zoos: labeled Survives **5%** of the time, while DSR confidence
  > 0.5 alone would flag 57.5% of them.
- Winners with planted Sharpe 1.0 / 1.5 / 2.0 labeled Survives **52.9% /
  82.5% / 97.5%** of the time.

## Challenges

- **DSR alone is overconfident.** DSR assumes independent trials; on synthetic
  noise zoos, DSR confidence > 0.5 alone would flag 57.5% of them.
  The full battery (PBO, Reality Check, degradation, costs, length) brings
  that to 5%, which is why the verdict is a battery, not one number.
- **Units.** PSR, DSR and MinTRL are defined in per-period Sharpe units, while
  the UI shows annualized Sharpes. We convert internally and unit-test known
  cases (annualized SR 0.5 over 252 days → PSR ≈ 0.69).
- **Monthly data.** Supporting the licensed monthly Pink Sheet meant making
  every annualization, MinTRL and narrative frequency-aware (12 vs 252
  periods per year).
- **Proving no-lookahead.** A test whose *leaked* signal would earn |r| every
  bar shows the shifted implementation earns ~0.

## Accomplishments that we're proud of

- The verdict label itself is validated on ground truth (E2: 81.9% accuracy,
  5% Survives on pure noise).
- On 55 years of licensed World Bank data, Mirage refuses to call strong-looking
  gold and Brent searches Survives because the Reality Check does not
  find sufficient evidence of outperformance (E4).
- Seeded, offline reproduction: `python -m experiments.run_all e2` and
  `python -m experiments.run_all e4` regenerate every submitted figure.
- A public API built for abuse: bounded grids and uploads, a concurrency cap,
  server-generated program IDs, same-origin CORS, and regression tests for
  each.

## What we learned

Single-test overfitting detectors are overconfident when their assumptions
fail. A battery with a visible component table is more honest, and a
detector's own error rates belong next to its verdicts.

## What's next for Mirage

- Signatures and an external anchor for the chain head (for example a
  transparency log), so a third party could check a program's history without
  trusting the server. Today's certificates are unsigned and nothing is
  anchored.
- Grid pre-registration: refuse trials outside a registered search space.
- More diagnostics: SPA test (Hansen 2005), stepwise RC, Bayesian PBO.
- More license-checked data sources, including investable return series.

## Try it out

- **Live app:** [DEPLOYED URL — pending deploy approval and smoke test]
- **Source:** https://github.com/sharonbasovich/mirage
- **Demo video:** [YOUTUBE URL — human uploads; script in submission/VIDEO_SCRIPT.md]

## Built With

python · numpy · pandas · scipy · scikit-learn · fastapi · uvicorn · typer ·
sqlite · pytest · ruff · mypy · react · vite · typescript · tailwind-css ·
recharts · matplotlib · playwright · ffmpeg · piper-tts ·
world-bank-pink-sheet · docker · github-actions · **devin (cognition-ai)**

## Data & citations

- **Submitted data:** World Bank Commodity Price Data (The Pink Sheet),
  monthly nominal USD reference prices for 15 commodities, 1971–2026, licensed
  **CC BY 4.0** (https://datacatalog.worldbank.org/search/dataset/0038238;
  license: https://datacatalog.worldbank.org/public-licenses). Attribution:
  "World Bank Commodity Price Data (The Pink Sheet), World Bank." Mirage bundles a
  transformed subset: the workbook's "Monthly Prices" sheet converted to CSV,
  15 columns and rows from 1971-01 selected, columns renamed to `WB_*`
  symbols, numeric values preserved as published. The demo, video, figures and tests use only
  this data plus synthetic series.
- **Outside the submission (optional, user-local):** the code can also load
  daily Yahoo Finance data that a user fetches into their own local cache with
  `scripts/fetch_data.py` (via `yfinance`). That data is governed by Yahoo's
  terms (https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html), is not
  bundled or redistributed, carries no license from Mirage, and is not used in
  any submitted evidence, figure, screenshot or video.
- Bailey & López de Prado (2012) *The Sharpe Ratio Efficient Frontier*;
  (2014) *The Deflated Sharpe Ratio*; Bailey, Borwein, López de Prado & Zhu
  (2017) *The Probability of Backtest Overfitting*; López de Prado (2018)
  *Advances in Financial Machine Learning* (purged CV); White (2000) *A Reality
  Check for Data Snooping*; Politis & Romano (1994) stationary bootstrap;
  Harvey & Liu (2015) *Backtesting*.

## AI assistance disclosure

Substantially all code, documentation, and the demo video script were drafted
with Devin (Cognition AI) under human direction: the human defined the scope,
reviewed the output, and directed testing.

## Disclaimer

This is a research prototype built for GIBC V2. It is not a product, not a
financial service, and not financial advice. Historical simulation only; no
live trading and no real money.
