# Mirage

**The backtest lie detector.**

> This is a research prototype built for GIBC V2. It is not a product, not a
> financial service, and not financial advice.

Anyone can build a trading strategy with a 300% backtest. Almost none survive
live. The reason is not bad code — it is *selection bias*: try 500 parameter
combinations, keep the best, and the "best" backtest is mostly luck. Clinical
trials solved this decades ago with pre-registration and multiple-testing
corrections; quant research mostly has not.

Mirage is a free, open-source system that:

1. **Backtests** strategies on real market data with realistic frictions
   (strict no-lookahead, transaction costs, slippage, optional vol targeting),
2. **Records every trial** in a tamper-evident, hash-chained **Trial Ledger** —
   pre-registration for backtests: you cannot quietly delete the losers, and
3. Runs a battery of **overfitting diagnostics** from the academic literature —
   Deflated Sharpe Ratio, Probability of Backtest Overfitting via CSCV,
   purged walk-forward CV, a stationary-bootstrap Reality Check, cost
   fragility, and minimum backtest length — and renders a plain-English
   **verdict card** a person can act on.

It also **validates itself**: because we can synthesize strategies with *known*
zero skill (and planted skill), we measure the detector's false-positive rate
and detection power, and publish ROC curves.

## Demo

- **Live app:** see `submission/DEVPOST.md` for the deployed URL
- **Screenshots:** `submission/screenshots/`
- **Experiment figures:** `reports/figures/`

## Quick start

Prerequisites: Python ≥ 3.11, Node ≥ 20 (only for the web UI), ~2 GB disk.

```bash
git clone https://github.com/sharonbasovich/mirage.git && cd mirage
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core lib, CLI, API, dev tools
pytest                            # 29 unit tests
```

Run the full web app (serves the built frontend from FastAPI, single origin):

```bash
cd frontend && npm ci && npm run build && cd ..
uvicorn mirage.api:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

Or with Docker (no local toolchain needed):

```bash
docker compose up --build
# open http://localhost:8000
```

### CLI

```bash
mirage run ma_cross --symbols SPY --grid "fast=5,10,20;slow=100,200" --analyze
mirage audit my_returns.csv --trials 40      # audit an external backtester's output
mirage report <program-id>                   # pre-registration certificate JSON
mirage programs                              # list recorded programs
mirage experiments                           # rerun E1-E3
```

Every `mirage run` (and every UI/API run) appends hash-chained entries to the
SQLite Trial Ledger at `data/ledger.sqlite3`.

## What the diagnostics do

| Diagnostic | Question answered | Method |
|---|---|---|
| Sharpe / PSR | Is the best trial's Sharpe significant alone? | Bailey & López de Prado 2012 (skew/kurtosis-adjusted) |
| **DSR** | Is it significant *given N trials were tried*? | Bailey & López de Prado 2014 — expected max Sharpe under no skill |
| **PBO (CSCV)** | Probability the IS winner underperforms OOS | Bailey, Borwein, López de Prado & Zhu 2017 — combinatorially symmetric CV, S=16 blocks, rank logits |
| Purged CV | Is ML skill real or leakage? | López de Prado 2018 — purged k-fold + embargo, walk-forward |
| Reality Check | Could the best-of-N edge be luck? | White 2000 + Politis–Romano stationary bootstrap |
| Cost fragility | How much cost kills it? | Sharpe-vs-bps curve → breakeven |
| MinBTL | Is the backtest long enough? | Bailey & López de Prado 2014 |
| Haircuts | P-value correction for N tests | Bonferroni / Holm / BHY (Harvey & Liu 2015) |

Outputs fold into a transparent **Mirage Score 0–100** (weights visible in the
UI and in `mirage/diagnostics/verdict.py`) → **Survives / Unclear / Mirage**.

Backtester convention: signal at close *t* → position from *t+1*
(`pos.shift(1)`); a unit test proves a leaked signal would be flagged.

## Validation results (rerun: `make experiments`)

**E1 — false positives.** 1,000 random zero-skill signal strategies on real
SPY returns. Best in-sample Sharpe = **0.61** — looks fine, and naive PSR
certifies it at 99.8%! But the DSR threshold (expected max Sharpe under
luck) = **0.69** → DSR p = **0.36**, CSCV PBO = **0.73**, Reality Check
p = **1.00** → verdict **Mirage (24/100)**. Over 20 independent 100-strategy
zoos: DSR alone fails to flag **45%** of zoos (correlated trials share SPY's
drift — a real, honest finding), PBO alone misses **5%**, and **the full
verdict battery misses 0%** — every zero-skill zoo is labeled Mirage or
Unclear, none Survives. This is exactly why the verdict uses multiple
independent diagnostics.

**E2 — detection power + label validation.** Synthetic markets with planted,
tunable true skill (8 levels × 40 reps × 50 strategies, T = 2500): among reps
where the skilled strategy wins IS, the verdict says **Survives in
53%/82%/98%** at planted Sharpe 1.0/1.5/2.0 — Sharpe 1.0 is the honest
detection boundary (on the misses the realized Sharpe landed ~0.65–0.98).
ROC AUC: **DSR 0.91, PBO 0.90**. The verdict *label itself* is validated on
ground truth: treating Survives as the classifier, confusion matrix
TP 102 / FP 5 / FN 53 / TN 160 → **82% accuracy**; only **5%** of pure-noise
zoos are ever labeled Survives.

**E3 — real strategy report cards** (`reports/e3.json`):

| Program | Trials | Best IS Sharpe | DSR p | PBO | RC p | MinBTL | Score | Verdict |
|---|---|---|---|---|---|---|---|---|
| MA crossover grid, SPY | 15 | 0.80 | 0.998 | 0.65 | 0.97 | 1,114 | 60.3 | Unclear |
| TS-momentum grid, BTC | 12 | 1.09 | 0.999 | 0.09 | 0.03 | 548 | 95.0 | Survives |
| 12-1 sector momentum | 12 | 0.55 | 0.987 | 0.66 | 0.99 | 2,289 | 59.4 | Unclear |
| RSI mean-reversion, SPY | 36 | 0.66 | 0.947 | 0.29 | 0.99 | 1,529 | 66.1 | Unclear |
| ML classifier grid, SPY | 8 | 0.69 | 0.995 | 0.07 | 0.82 | 1,455 | 81.2 | Unclear |

Only the BTC momentum zoo survives: its best trial beats the BTC buy-and-hold
benchmark beyond luck (RC p = 0.03) and stays above the OOS median in 91% of
splits. The others post respectable in-sample Sharpes but fail the Reality
Check — which hard-caps the label at Unclear even when the score clears 65.

## How to reproduce every figure

```bash
pip install -e ".[dev]"          # data/ CSVs are committed — no network needed
make experiments                  # or: python -m experiments.run_all
# figures → reports/figures/*.png ; stats → reports/*.json
python -m experiments.run_all --only e1   # one experiment only
```

All experiments are seeded. Runtime: ~10 min on a laptop CPU.

## Repository layout

```
mirage/                 core package
  data.py               CSV cache loader + data hash
  backtest.py           vectorized no-lookahead backtester
  strategies/           ma_cross, tsmom, sector_mom, rsi_rev, bollinger, ml_daily
  diagnostics/          sharpe/psr/dsr/minbtl, cscv (PBO), purged CV, reality
                        check, cost fragility, haircuts, verdict composer
  ledger.py             SQLite hash-chained Trial Ledger + certificate export
  program.py            trial runner + analysis pipeline
  api.py                FastAPI backend (serves frontend build, single origin)
  cli.py                `mirage` CLI (typer)
experiments/            E1/E2/E3 self-validation (seeded, -> reports/)
frontend/               React + Vite + TS + Tailwind + Recharts
tests/                  pytest suite (29 tests)
scripts/fetch_data.py   refreshes the data/ cache (yfinance)
submission/             Devpost writeup, video script, screenshots, checklist
```

## Data

Daily OHLCV CSVs committed under `data/` (18 symbols: SPY, QQQ, IWM, TLT, GLD,
9 SPDR sector ETFs, BTC-USD, ETH-USD; inception→2026-09) fetched with
[yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance; data for
research/educational use — see the provider's terms). Refresh with
`python scripts/fetch_data.py`. Each ledger entry embeds a SHA-256 hash of the
CSV set so a certificate is bound to the exact data.

## AI assistance disclosure

Substantially all code, documentation, and the demo video script in this
repository were drafted with **Devin (Cognition AI)** under human direction:
the human defined the scope, reviewed the output, and directed testing.
Statistical methods follow the cited academic sources.

## Team

- **Sharon Basovich** — University of Waterloo, CS
- **Terry** *(second teammate — TBD)*

## Built With

Python · numpy · pandas · scipy · scikit-learn · FastAPI · uvicorn · typer ·
SQLite · pytest · ruff · mypy · React 18 · Vite · TypeScript · Tailwind CSS ·
Recharts · matplotlib · yfinance (Yahoo Finance data) · Docker ·
GitHub Actions · Devin deploy (Fly.io infra) · **Devin (Cognition AI)**

## License

MIT — © 2026 Sharon Basovich (and Terry — second teammate TBD). See `LICENSE`.
