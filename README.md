# Mirage

**The backtest lie detector.**

> This is a research prototype built for GIBC V2. It is not a product, not a
> financial service, and not financial advice.

Try enough parameter combinations, keep the best, and part of the "best"
backtest is luck. That is *selection bias*, and it is invisible when only the
winner is reported. Clinical
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
and detection power, and report ROC curves.

## Demo

- **Devpost:** https://devpost.com/software/mirage-1vh78d (submitted, GIBC V2 Track 02)
- **Demo video:** https://www.youtube.com/watch?v=Q3b8egv8syM (3:03, narrated)
- **Live app:** https://mirage-swart.vercel.app (FastAPI + Vite on Vercel Hobby,
  single project). Stored programs/ledger/certificates are **temporary, shared
  and per-instance** — they reset on cold starts/scale-out; every run is
  computed live and nothing is durable storage. The UI banner says the same.
- **Source:** https://github.com/sharonbasovich/mirage
- **Screenshots:** `submission/screenshots/`
- **Experiment figures:** `reports/figures/`

## Quick start

Prerequisites: Python ≥ 3.11, Node ≥ 20 (only for the web UI), ~2 GB disk.

```bash
git clone https://github.com/sharonbasovich/mirage.git && cd mirage
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core lib, CLI, API, dev tools
pytest                            # 83 tests, offline (bundled World Bank data + synthetic)
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
mirage audit monthly.csv --trials 40 --frequency monthly --benchmark WB_GOLD
mirage report <program-id>                   # unsigned trial-ledger certificate JSON
mirage programs                              # list recorded programs
mirage experiments                           # rerun E2 + E4 (E1/E3 only with a local Yahoo cache)
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
later, a user would have to record its chain head somewhere they don't
control (a git commit, a post); Mirage does not do this, and no chain head
from the demo has been published. The idea is borrowed from clinical
pre-registration, but Mirage doesn't enforce it on its own.

### Audit uploads

`mirage audit` (and `POST /api/audit`) expects **one column of decimal simple
returns per tried configuration** (0.01 = +1%); a `date`/`timestamp`/`time`
column is optional. Inputs are validated before any diagnostic runs and
refused with an explicit error — never silently filled or guessed at — when
they contain missing, blank, non-finite or non-numeric cells (truly empty
lines are skipped by the CSV parser, but comma-only rows and any missing
return cell are refused — a 40-blank-row upload is refused, not trimmed),
values |r| ≥ 1
(a **supported-range restriction** — not a claim that every ≥100% return is
impossible; convert percent units or price levels to decimals), columns that
are near-constant (dispersion below float64 cancellation scale) or
near-riskless (per-period |mean|/sd ≥ 1 — genuine cash-like series are
outside this prototype's supported range), fewer than 64 rows, fewer than 2
return columns, or a declared trial count below the uploaded column count.
Percent strings like `1%` are rejected; not every mistaken unit is
detectable, so check the file's units before uploading.

A declared count above the uploaded columns extrapolates the luck threshold
from the uploaded columns — the verdict narrative says so and notes unseen
trials were not seen — and the label is **capped at Unclear** regardless of
the heuristic score (which is still shown, flagged `label_capped`): an
extrapolated DSR is assumption-dependent, and PBO/Reality Check use only the
uploaded configurations, so a subset can never certify the unseen part of a
search. Even a full-matrix Survives relies on a truthful declared count and
uploading every tried configuration. The extrapolation itself is refused
when the uploaded Sharpes are near-identical (cross-trial variance then
unestimable). PBO over few uploaded columns is marked as a coarse estimate
in the component detail.

Dates follow a supported-calendar contract: median spacing must be ~1 day
(0.9–3d, one row per calendar day) or monthly (20–40d, one row per month) —
intraday, weekly, quarterly or irregular series are refused, as are
duplicate normalized days/months. With dates present the declared
`frequency` is verified against the data (a monthly file labelled daily is
refused); **without dates the frequency is user-declared and unverifiable** —
the result carries `frequency_verified: false`, a narrative note and a UI
badge.

An optional `benchmark` is inner-joined on the uploaded dates
(month-aligned for monthly series) — never aligned by position. It requires
a usable date column, ≥ 64 overlapping periods that are consecutive in the
benchmark calendar, and a matching frequency; uploaded rows outside the
benchmark's coverage are dropped and the count is reported
(`benchmark_dropped_rows`). If any of that fails the audit is refused rather
than silently omitting the benchmark.

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
| Sharpe / PSR | Confidence that the best trial's true Sharpe exceeds a benchmark (not a p-value) | Bailey & López de Prado 2012 (skew/kurtosis-adjusted) |
| **DSR** | Confidence it exceeds the best-of-N luck threshold (not P(skill)) | Bailey & López de Prado 2014 — expected max Sharpe under no skill |
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

## Validation results (submitted evidence)

The submitted evidence is **E2** (synthetic) and **E4** (bundled World Bank
Pink Sheet, CC BY 4.0). Both reproduce fully offline. DSR values below are
*confidence (exceedance) estimates* that the true Sharpe exceeds the
best-of-N luck threshold. They are not p-values and not the probability that
genuine skill exists. A large Reality Check p means insufficient evidence of
outperformance, not proof of no edge.

**E2 — detection power + label validation** (`reports/e2.json`). Synthetic
markets with planted, tunable true skill (8 levels × 40 reps × 50 strategies,
T = 2,500). ROC AUC for "the IS winner has true skill": **DSR 0.914, PBO
0.900**. Treating the Survives label as the classifier: TP 102 / FP 5 / FN 53
/ TN 160, **81.9% accuracy**. On pure-noise zoos the label says Survives
**5%** of the time, while DSR confidence > 0.5 alone would flag 57.5%. Winners
with planted Sharpe 1.0 / 1.5 / 2.0 are labeled Survives 52.9% / 82.5% /
97.5% of the time.

**E4 — World Bank report cards** (`reports/e4.json`,
`reports/figures/e4_worldbank_scorecard.png`), 1971-01 → 2026-08 (668 months).
Benchmark = equal-weight buy-and-hold of the program's own assets. These are
**hypothetical price-series backtests**: Pink Sheet values are monthly
reference/spot prices, not an investable return series or executable bars,
so the results illustrate the diagnostics and are not realizable trading
P&L. Futures roll, storage, financing and execution details are not modeled.

| Program | Trials | Best IS Sharpe | DSR confidence | PBO | RC p | Score | Verdict |
|---|---|---|---|---|---|---|---|
| MA crossover, gold | 12 | 0.71 | 1.000 | 0.23 | 0.59 | 81.2 | Unclear |
| TS-momentum, Brent | 10 | 0.62 | 1.000 | 0.01 | 0.52 | 87.4 | Unclear |
| Cross-sectional momentum, 8 commodities | 12 | 0.34 | 0.967 | 0.27 | 0.99 | 68.7 | Unclear |
| RSI mean-reversion, gold | 27 | 0.23 | 0.467 | 0.30 | 1.00 | 51.8 | Unclear |

Gold trend-following and Brent momentum pass DSR and PBO, but the Reality
Check finds insufficient evidence that either outperforms holding the asset
after data snooping (RC p > 0.5), so Mirage won't call either one Survives.

One caveat on that cap: the RC p is a bootstrap estimate, so it moves with
the resampling seed, and Brent's sits near the 0.5 cutoff — across 40 seeds
it ranged 0.470–0.572 and the label flipped between Survives and Unclear 19
times (gold's did not flip once). The 0.5 threshold is a heuristic, not a
calibrated significance level; a borderline RC p should be read as genuinely
undecided, and rerunning can nudge Brent across the line.

**Optional local experiments (outside the submission).** E1 (random zero-skill
zoos) and E3 (daily ETF/crypto report cards) run only on daily Yahoo data a
user fetches into their own cache. That data is not bundled, not
redistributed, and not used in any submitted figure, screenshot, video or
number, so no E1/E3 results are reported here.

## How to reproduce every figure

```bash
pip install -e ".[dev,data]"
python -m experiments.run_all e2  # synthetic, offline
python -m experiments.run_all e4  # bundled World Bank data, offline
# figures → reports/figures/*.png ; stats → reports/*.json
# optional, outside the submission: python scripts/fetch_data.py (user-local
# Yahoo fetch under Yahoo's terms), then make experiments to add E1/E3
```

All experiments are seeded. Without a Yahoo cache, E1/E3 are skipped with a
message and E2/E4 still run offline. Yahoo revises history and adjusted
prices, so a local E1/E3 run is not exactly reproducible. The data hash stored
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
tests/                  pytest suite (83 tests, incl. API abuse regressions)
data/worldbank/         bundled World Bank Pink Sheet subset (CC BY 4.0)
scripts/fetch_data.py   user-local Yahoo fetch (not redistributed)
scripts/fetch_worldbank.py  rebuilds the World Bank subset from the official workbook
submission/             Devpost writeup, video script, screenshots, checklist
```

## Data

| Dataset | Status in repo | Source | License / terms |
|---|---|---|---|
| **World Bank Commodity Price Data (The Pink Sheet)** — monthly nominal USD prices, 15 commodities (`WB_GOLD`, `WB_SILVER`, `WB_PLATINUM`, `WB_COPPER`, `WB_ALUMINUM`, `WB_ZINC`, `WB_NICKEL`, `WB_BRENT`, `WB_NATGAS_US`, `WB_WHEAT`, `WB_MAIZE`, `WB_SOYBEANS`, `WB_SUGAR`, `WB_COFFEE`, `WB_COTTON`), 1971-01 → 2026-08 | **Bundled** at `data/worldbank/pinksheet_monthly.csv` (72 KB subset of the official workbook, rebuilt by `scripts/fetch_worldbank.py`) | [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets); [data catalog entry](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) | [CC BY 4.0](https://datacatalog.worldbank.org/public-licenses). Attribution: "World Bank Commodity Price Data (The Pink Sheet), World Bank." Changes: this is a **transformed subset** — converted from the source workbook's "Monthly Prices" sheet (Excel) to CSV, 15 commodity columns and rows from 1971-01 selected, columns renamed to `WB_*` symbols; the numeric price values are preserved as published. |
| **Yahoo Finance daily OHLCV** — SPY, QQQ, IWM, TLT, GLD, 11 SPDR sector ETFs, BTC-USD, ETH-USD | **Not bundled.** Each user downloads it with `python scripts/fetch_data.py` (yfinance) into `$MIRAGE_YAHOO_DIR` (default `~/.cache/mirage/yahoo`) | Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) | Subject to [Yahoo's terms of service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html). Mirage makes no redistribution claim; yfinance's Apache-2.0 license covers the library, not the data. |

The submitted demo, video, figures and the test suite use only the bundled
World Bank data (plus synthetic series). Yahoo support is an optional,
user-local feature outside the submission; Mirage grants no license to Yahoo
data. Yahoo symbols appear in the UI only when a local cache
exists. One program can't mix monthly and daily symbols; annualization uses
12 or 252 periods per year to match. Each ledger entry stores a SHA-256 of
the exact data files used. Git history before this change still contains the
earlier Yahoo CSVs; purging them requires a history rewrite on the published
repo.

## AI assistance disclosure

Substantially all code, documentation, and the demo video script in this
repository were implemented and reviewed by AI agents (**Devin, Cognition
AI**) under the owner's authorization and direction: the owner defined the
scope and requirements and authorized the work, while design,
implementation, review and testing were AI-led. Statistical methods follow
the cited academic sources.

## Team

- **Sharon Basovich**, University of Waterloo, CS

## Built With

Python · numpy · pandas · scipy · scikit-learn · FastAPI · uvicorn · typer ·
SQLite · pytest · ruff · mypy · React 18 · Vite · TypeScript · Tailwind CSS ·
Recharts · matplotlib · Playwright · FFmpeg · Piper TTS · World Bank Pink
Sheet (CC BY 4.0) · yfinance (optional, user-local, outside the submission) ·
Docker · GitHub Actions · **Devin (Cognition AI)**

## License

Code: MIT, © 2026 Sharon Basovich (see `LICENSE`). Bundled World Bank data:
CC BY 4.0, © World Bank (see `data/worldbank/README.md`).
