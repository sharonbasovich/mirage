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

1. **Backtests** strategies on historical market data with realistic frictions
   (strict no-lookahead, transaction costs, slippage, optional vol targeting),
2. **Records every trial** in a hash-chained SQLite **Trial Ledger**, so the
   Deflated Sharpe Ratio uses the recorded trial count rather than one the user
   types in (see [what the ledger does and does not guarantee](#trial-ledger-guarantees)), and
3. Runs a battery of **overfitting diagnostics** from the academic literature —
   Deflated Sharpe Ratio, Probability of Backtest Overfitting via CSCV,
   purged walk-forward CV, a stationary-bootstrap Reality Check, cost
   fragility, and minimum backtest length — and renders a plain-English
   **verdict card** a person can act on.

It also **validates itself**: because we can synthesize strategies with *known*
zero skill (and planted skill), we measure the detector's false-positive rate
and detection power, and publish ROC curves.

## Demo

- **Live app:** not deployed yet (the free Devin backend deploy is waiting for approval)
- **Source:** https://github.com/sharonbasovich/mirage
- **Screenshots:** `submission/screenshots/`
- **Experiment figures:** `reports/figures/`

## Quick start

Prerequisites: Python ≥ 3.11, Node ≥ 20 (only for the web UI), ~2 GB disk.

```bash
git clone https://github.com/sharonbasovich/mirage.git && cd mirage
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core lib, CLI, API, dev tools
pytest                            # 54 tests, offline (bundled World Bank data + synthetic)
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
mirage run ma_cross --symbols WB_GOLD --grid "fast=2,3,6;slow=12,24"   # bundled monthly data
mirage run ma_cross --symbols SPY --grid "fast=5,10,20;slow=100,200"   # after fetching Yahoo data
mirage audit my_returns.csv --trials 40      # audit an external backtester's output
mirage report <program-id>                   # unsigned trial-ledger certificate JSON
mirage programs                              # list recorded programs
mirage experiments                           # rerun E1-E4
```

Every `mirage run` (and every UI/API run) appends hash-chained entries to the
SQLite Trial Ledger at `$MIRAGE_STATE_DIR/ledger.sqlite3` (default
`~/.local/share/mirage/`).

### Trial Ledger guarantees

Each entry stores the previous entry's SHA-256, so `verify_chain` detects an
edit or deletion made inside an otherwise intact ledger without recomputing
the rest of the chain. The ledger is **not signed and not externally
anchored**. Anyone with write access to the SQLite file can rewrite the whole
database and recompute every hash, and nothing in the file reveals that. The
exported certificate is a plain JSON summary (trial count, best trial, chain
head, verdict), not a digital signature. To make a program's history checkable
later, publish its chain head somewhere you don't control (a git commit, a
post) when you start. The idea is borrowed from clinical pre-registration, but
Mirage doesn't enforce it on its own.

### Public API limits

The FastAPI server is safe to expose without authentication. It enforces:
server-generated program IDs, with path parameters checked against
`^[A-Za-z0-9_-]{1,80}$` and kept inside the analysis directory; at most 12
symbols, 10 grid parameters, 12 values per parameter, 100 trials per run (16
for the ML family), and numeric parameters with |x| ≤ 2000; costs ≤ 500 bps;
audit uploads ≤ 5 MiB, ≤ 10,000 rows, ≤ 100 columns, declared trials ≤
100,000; `MIRAGE_MAX_CONCURRENT_RUNS` (default 2) concurrent runs/audits, with
HTTP 429 beyond that; the 200 most recent stored analyses. CORS is off
(same-origin only) unless `MIRAGE_CORS_ORIGINS` lists explicit origins.
Regression tests are in `tests/test_api_security.py`.

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

Backtester convention: signal at close of bar *t* → position from bar *t+1*
(`pos.shift(1)`); a unit test proves a leaked signal would be flagged.

## Validation results (rerun: `make experiments`)

> E1 and E3 use daily Yahoo data that each user fetches locally
> (`python scripts/fetch_data.py`, see [Data](#data)); the numbers below come
> from a fetch through 2026-09. E2 is synthetic and E4 uses the bundled,
> CC BY 4.0 World Bank data, so both reproduce fully offline.

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

**E4 — licensed, offline report cards** on World Bank monthly commodity
prices, 1971-01 → 2026-08 (668 months; `reports/figures/e4_worldbank_scorecard.png`).
Benchmark = equal-weight buy-and-hold of the program's own assets:

| Program | Trials | Best IS Sharpe | DSR p | PBO | RC p | Score | Verdict |
|---|---|---|---|---|---|---|---|
| MA crossover, gold | 12 | 0.71 | 1.000 | 0.23 | 0.59 | 81.2 | Unclear |
| TS-momentum, Brent | 10 | 0.62 | 1.000 | 0.01 | 0.52 | 87.4 | Unclear |
| Cross-sectional momentum, 8 commodities | 12 | 0.34 | 0.967 | 0.27 | 0.99 | 68.7 | Unclear |
| RSI mean-reversion, gold | 27 | 0.23 | 0.467 | 0.30 | 1.00 | 51.8 | Unclear |

Over 55 years, gold trend-following and Brent momentum pass DSR and PBO, but
neither beats simply holding the asset by more than luck would explain
(RC p > 0.5), so Mirage won't call either one Survives.

## How to reproduce every figure

```bash
pip install -e ".[dev,data]"
python scripts/fetch_data.py      # E1/E3 only: user-local Yahoo fetch (network, Yahoo terms)
make experiments                  # or: python -m experiments.run_all
# figures → reports/figures/*.png ; stats → reports/*.json
python -m experiments.run_all e4  # one experiment only (e2 and e4 need no network)
```

All experiments are seeded. Without a Yahoo cache, E1/E3 are skipped with a
message and E2/E4 still run offline. Yahoo revises history and adjusted
prices, so a later fetch can move E1/E3 numbers slightly. The data hash stored
in each ledger entry records exactly which bytes were used. Runtime: ~10 min
on a laptop CPU.

## Repository layout

```
mirage/                 core package
  data.py               bundled World Bank + user-local Yahoo loaders, data hash
  backtest.py           vectorized no-lookahead backtester
  strategies/           ma_cross, tsmom, sector_mom, rsi_rev, bollinger, ml_daily
  diagnostics/          sharpe/psr/dsr/minbtl, cscv (PBO), purged CV, reality
                        check, cost fragility, haircuts, verdict composer
  ledger.py             SQLite hash-chained Trial Ledger + certificate export
  program.py            trial runner + analysis pipeline
  api.py                FastAPI backend (serves frontend build, single origin)
  cli.py                `mirage` CLI (typer)
experiments/            E1-E4 self-validation (seeded, -> reports/)
frontend/               React + Vite + TS + Tailwind + Recharts
tests/                  pytest suite (54 tests, incl. API abuse regressions)
data/worldbank/         bundled World Bank Pink Sheet subset (CC BY 4.0)
scripts/fetch_data.py   user-local Yahoo fetch (not redistributed)
scripts/fetch_worldbank.py  rebuilds the World Bank subset from the official workbook
submission/             Devpost writeup, video script, screenshots, checklist
```

## Data

| Dataset | Status in repo | Source | License / terms |
|---|---|---|---|
| **World Bank Commodity Price Data (The Pink Sheet)** — monthly nominal USD prices, 15 commodities (`WB_GOLD`, `WB_SILVER`, `WB_PLATINUM`, `WB_COPPER`, `WB_ALUMINUM`, `WB_ZINC`, `WB_NICKEL`, `WB_BRENT`, `WB_NATGAS_US`, `WB_WHEAT`, `WB_MAIZE`, `WB_SOYBEANS`, `WB_SUGAR`, `WB_COFFEE`, `WB_COTTON`), 1971-01 → 2026-08 | **Bundled** at `data/worldbank/pinksheet_monthly.csv` (72 KB subset of the official workbook, rebuilt by `scripts/fetch_worldbank.py`) | [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets); [data catalog entry](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) | [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses). Attribution: "World Bank Commodity Price Data (The Pink Sheet), World Bank." We extracted a subset and changed nothing else. |
| **Yahoo Finance daily OHLCV** — SPY, QQQ, IWM, TLT, GLD, 11 SPDR sector ETFs, BTC-USD, ETH-USD | **Not bundled.** Each user downloads it with `python scripts/fetch_data.py` (yfinance) into `$MIRAGE_YAHOO_DIR` (default `~/.cache/mirage/yahoo`) | Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Subject to [Yahoo's terms of service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html). Mirage makes no redistribution claim; yfinance's Apache-2.0 license covers the library, not the data. |

The public demo and the test suite use only the bundled World Bank data (plus
synthetic series). Yahoo symbols appear in the UI only when a local cache
exists. One program can't mix monthly and daily symbols; annualization uses
12 or 252 periods per year to match. Each ledger entry stores a SHA-256 of
the exact data files used. Git history before this change still contains the
earlier Yahoo CSVs; purging them requires a history rewrite on the published
repo.

## AI assistance disclosure

Substantially all code, documentation, and the demo video script in this
repository were drafted with **Devin (Cognition AI)** under human direction:
the human defined the scope, reviewed the output, and directed testing.
Statistical methods follow the cited academic sources.

## Team

- **Sharon Basovich**, University of Waterloo, CS

## Built With

Python · numpy · pandas · scipy · scikit-learn · FastAPI · uvicorn · typer ·
SQLite · pytest · ruff · mypy · React 18 · Vite · TypeScript · Tailwind CSS ·
Recharts · matplotlib · World Bank Pink Sheet (CC BY 4.0) · yfinance
(optional, user-local Yahoo fetch) · Docker · GitHub Actions ·
Devin deploy (built-in, free) · **Devin (Cognition AI)**

## License

Code: MIT, © 2026 Sharon Basovich (see `LICENSE`). Bundled World Bank data:
CC BY 4.0, © World Bank (see `data/worldbank/README.md`).
