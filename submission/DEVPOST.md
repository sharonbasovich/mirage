# Devpost submission — Mirage

> Fill the bracketed placeholders, then paste each section into Devpost.

**Project name:** Mirage

**Tagline (≤60 chars):** The backtest lie detector.

**Elevator pitch:** Anyone can build a trading strategy with a 300% backtest.
Almost none survive live. Mirage records every trial in a tamper-evident ledger
and runs the academic overfitting-diagnostics battery — DSR, PBO, purged CV,
Reality Check — to tell you, in plain English, whether your backtest is real.

---

## Inspiration

Hackathon projects — and real retail quant posts — love a great backtest. But
the Sharpe you see is the *best of N tries*, and nobody reports N. Clinical
trials solved exactly this problem with pre-registration and multiple-testing
corrections; quantitative finance has the same math (Bailey & López de Prado;
White's Reality Check; Harvey–Liu haircuts) but almost no tooling a student or
retail quant can actually use. We built Mirage to make "did my strategy
overfit?" a one-click question — and to make cherry-picking trials
cryptographically inconvenient.

## What it does

- **Backtester:** vectorized daily engine with strict no-lookahead
  (signal at close *t* → position from *t+1*), costs + slippage in bps, optional
  volatility targeting. Strategy library: MA crossover, time-series momentum,
  12-1 cross-sectional sector momentum, RSI and Bollinger mean reversion,
  buy-and-hold, and a gradient-boosted ML classifier trained with purged
  walk-forward CV + embargo.
- **Trial Ledger:** every trial — UI, CLI, or API — appends to a SQLite
  hash-chained ledger (each entry's hash includes the previous entry's). It is
  pre-registration for backtests: you can't quietly delete the losers.
  Exports a signed "Backtest Pre-registration Certificate" JSON per research
  program.
- **Diagnostics battery:** Deflated Sharpe Ratio (Bailey & López de Prado
  2014), Probability of Backtest Overfitting via CSCV (Bailey, Borwein, López
  de Prado & Zhu 2017), purged CV, stationary-bootstrap Reality Check (White
  2000), cost-fragility breakeven, minimum backtest length, and
  Bonferroni/Holm/BHY haircuts (Harvey & Liu 2015).
- **Verdict card:** a transparent 0–100 Mirage Score with the component table
  always visible, plus rule-generated plain-English sentences (no LLM) —
  "Do not trade this: 73% probability the in-sample winner underperforms OOS."
- **Upload-audit:** paste any returns CSV from *another* backtester plus a
  declared trial count and get the same verdict — Mirage audits the field, not
  just its own runs.
- **Self-validation:** Mirage publishes its own error rates — false-positive
  rate, detection power, ROC/AUC — measured on synthetic strategies with
  known zero / planted skill.

## How we built it

Pure statistics — no LLM in the product. Python (numpy/pandas/scipy/
scikit-learn) core package; FastAPI backend serving a React + TypeScript +
Tailwind + Recharts single-origin app; SQLite ledger; typer CLI; matplotlib
figures; pytest + ruff + mypy; Docker; GitHub Actions CI.

The math follows the papers: DSR deflates the best Sharpe by the expected
maximum under luck given the *variance of trial Sharpes* (not just N);
CSCV partitions the returns matrix into S=16 blocks over all C(16,8)=12,870
combinations and measures P(λ<0) of the rank logits; the Reality Check uses a
stationary bootstrap (Politis–Romano) around the benchmark-excess distribution.

## Challenges

- **DSR's independence assumption fails on real zoos.** In E1, every trial is
  the same random signal generator on the same SPY series, so trial Sharpes are
  correlated — DSR alone misses 55% of zero-skill zoos at p=0.05. We turned
  that failure into the central finding: no single test is reliable; the
  combined battery misses only 5%.
- **PBO needs genuinely distinct trials.** On pure noise CSCV returns ~0.5 by
  construction, so our unit test had to plant a *localized* edge to show
  PBO→high vs a persistent edge → low.
- **Reality Check bandwidth.** Stationary-bootstrap block length trades bias
  vs variance; we validated avg_block=10 on both noise (p≈1) and planted-edge
  (p≈0) cases.
- **Proving no-lookahead.** We wrote a test whose *leaked* signal would earn
  |r| every day — the shifted implementation earns ~0, proving the convention.

## Accomplishments that we're proud of

- The tool catches *itself*: E1 shows a 1,000-strategy random zoo produces a
  "great" backtest (IS Sharpe 0.61) that Mirage correctly rejects
  (DSR p=0.001, PBO=0.73).
- Published detector error rates — E2 ROC AUC 0.81 (DSR) / 0.79 (PBO); a
  metrology tool that reports its own measurement error.
- The Trial Ledger: a 60-line hash chain that makes trial-deletion evident —
  pre-registration for backtests as a real, working artifact.
- One-command reproduction: `pip install -e . && make experiments` regenerates
  every figure and statistic in this writeup, fully offline.

## What we learned

Single-test overfitting detectors are dangerously overconfident on real data —
correlated trials break the independence math. The honest answer is a *battery*
plus a visible component table. Also: writing down the detector's own
false-positive rate is the difference between a metrology tool and another
confident number.

## What's next for Mirage

- Signed certificates (asymmetric) so a third party can verify a program's
  history without trusting our server.
- Ledger-to-verdict webhooks: pre-register a grid on GitHub and Mirage refuses
  trials outside the registered space.
- More diagnostics: SPA test (Hansen 2005), stepwise RC, full Bayesian PBO
  posterior.
- Multi-asset-class data connectors with license-checked sources.

## Try it out

- **Live app:** [DEPLOYED URL — paste here]
- **Source:** [GITHUB URL — https://github.com/sharonbasovich/mirage]
- **Demo video:** [YOUTUBE URL — human uploads; script in submission/VIDEO_SCRIPT.md]

## Built With

python · numpy · pandas · scipy · scikit-learn · fastapi · uvicorn · typer ·
sqlite · pytest · ruff · mypy · react · vite · typescript · tailwind-css ·
recharts · matplotlib · yfinance · docker · github-actions · flyio ·
**devin (cognition-ai)**

## Data & citations

- Market data: Yahoo Finance via `yfinance` (research/educational use; see
  provider terms). Daily OHLCV CSVs committed under `data/` — runs offline.
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
financial service, and not financial advice.
