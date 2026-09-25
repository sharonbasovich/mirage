"""Mirage API - FastAPI backend serving the React build (single origin)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from mirage.data import SYMBOLS, data_hash, list_symbols, load_close, load_ohlcv
from mirage.diagnostics.sharpe import dsr_expected_max_sharpe, psr, sharpe_ratio
from mirage.ledger import Ledger
from mirage.program import analyze_returns_matrix, analyze_trials, run_program
from mirage.strategies import STRATEGIES

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = ROOT / "data" / "analyses"
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(title="Mirage", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class RunRequest(BaseModel):
    family: str
    symbols: list[str]
    grid: dict[str, list[Any]] | None = None
    cost_bps: float = 5.0
    slippage_bps: float = 0.0
    vol_target: float | None = None
    program_id: str | None = None
    benchmark: str | None = "SPY"


DEMO_PRESETS: dict[str, dict[str, Any]] = {
    "ma_zoo": {
        "title": "MA-Crossover Zoo on SPY",
        "family": "ma_cross",
        "symbols": ["SPY"],
        "grid": {"fast": [5, 10, 20, 50], "slow": [50, 100, 150, 200], "long_only": [True]},
        "cost_bps": 5.0,
    },
    "btc_tsmom": {
        "title": "TS-Momentum Grid on BTC-USD",
        "family": "tsmom",
        "symbols": ["BTC-USD"],
        "grid": {"lookback": [7, 14, 21, 63, 126, 189], "long_only": [False, True]},
        "cost_bps": 15.0,
    },
    "sector_mom": {
        "title": "Sector Momentum (SPDR ETFs)",
        "family": "sector_mom",
        "symbols": ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"],
        "grid": {"lookback": [63, 126, 189, 252], "skip": [21], "top_k": [2, 3, 4]},
        "cost_bps": 5.0,
    },
    "rsi_zoo": {
        "title": "RSI Mean-Reversion Zoo on SPY",
        "family": "rsi_rev",
        "symbols": ["SPY"],
        "grid": {"window": [5, 10, 14, 21], "low": [20, 30, 40], "high": [60, 70, 80],
                 "long_only": [True]},
        "cost_bps": 5.0,
    },
    "ml_spy": {
        "title": "ML Direction Predictor on SPY",
        "family": "ml_daily",
        "symbols": ["SPY"],
        "grid": {
            "model": ["gbm"],
            "n_estimators": [50, 100],
            "max_depth": [2, 3],
            "learning_rate": [0.05, 0.1],
            "embargo": [2],
            "train_window": [504],
            "test_window": [63],
            "thresh": [0.0],
            "long_only": [True],
        },
        "cost_bps": 5.0,
    },
}


def _save_analysis(program_id: str, analysis: dict) -> None:
    (ANALYSIS_DIR / f"{program_id}.json").write_text(json.dumps(analysis))


def _load_analysis(program_id: str) -> dict | None:
    p = ANALYSIS_DIR / f"{program_id}.json"
    if p.exists():
        return json.loads(p.read_text())
    return None


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "data_hash": data_hash(SYMBOLS)[:16]}


@app.get("/api/symbols")
def symbols() -> list[dict]:
    out = []
    for s in list_symbols():
        df = load_ohlcv(s)
        out.append({
            "symbol": s,
            "rows": int(len(df)),
            "start": str(df.index[0].date()),
            "end": str(df.index[-1].date()),
        })
    return out


@app.get("/api/strategies")
def strategies() -> list[dict]:
    return [
        {
            "name": s.name,
            "description": s.description,
            "default_grid": s.default_grid,
            "default_symbols": s.default_symbols,
        }
        for s in STRATEGIES.values()
    ]


@app.get("/api/demos")
def demos() -> list[dict]:
    return [{"key": k, "title": v["title"], "family": v["family"],
             "symbols": v["symbols"], "grid": v["grid"], "cost_bps": v["cost_bps"]}
            for k, v in DEMO_PRESETS.items()]


@app.get("/api/programs")
def programs() -> list[dict]:
    progs = Ledger().programs()
    for p in progs:
        p["has_analysis"] = _load_analysis(p["program_id"]) is not None
    return progs


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    if req.family not in STRATEGIES:
        raise HTTPException(400, f"unknown family {req.family}")
    bad = [s for s in req.symbols if s not in SYMBOLS]
    if bad:
        raise HTTPException(400, f"uncached symbols {bad}")
    try:
        pid, trials = run_program(
            req.family, req.symbols, grid=req.grid,
            cost_bps=req.cost_bps, slippage_bps=req.slippage_bps,
            vol_target=req.vol_target, program_id=req.program_id,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"backtest failed: {exc}") from exc

    bench = None
    if req.benchmark and req.benchmark in SYMBOLS:
        bench = load_close(req.benchmark).pct_change().fillna(0.0)
    analysis = analyze_trials(trials, benchmark_returns=bench,
                              assumed_cost_bps=req.cost_bps)
    _save_analysis(pid, analysis)
    return {"program_id": pid, "analysis": analysis}


@app.post("/api/demo/{key}")
def run_demo(key: str) -> dict:
    if key not in DEMO_PRESETS:
        raise HTTPException(404, f"unknown demo {key}")
    p = DEMO_PRESETS[key]
    return run(RunRequest(
        family=p["family"], symbols=p["symbols"], grid=p["grid"],
        cost_bps=p["cost_bps"],
    ))


@app.get("/api/programs/{program_id}/analysis")
def program_analysis(program_id: str) -> dict:
    a = _load_analysis(program_id)
    if a is None:
        raise HTTPException(404, "no stored analysis for program (run it first)")
    return a


@app.get("/api/programs/{program_id}/trials")
def program_trials(program_id: str) -> list[dict]:
    entries = Ledger().entries(program_id)
    return [
        {
            "id": e.id, "ts": e.ts, "label": e.label, "config": e.config,
            "metrics": e.metrics, "config_hash": e.config_hash,
            "entry_hash": e.entry_hash, "prev_hash": e.prev_hash,
            "data_hash": e.data_hash,
        }
        for e in entries
    ]


@app.get("/api/programs/{program_id}/certificate")
def certificate(program_id: str) -> dict:
    led = Ledger()
    analysis = _load_analysis(program_id)
    cert = led.export_certificate(program_id, verdict=(analysis or {}).get("verdict"))
    cert["data_hash"] = data_hash(SYMBOLS)
    return cert


@app.get("/api/ledger/verify")
def ledger_verify() -> dict:
    ok, msg = Ledger().verify_chain()
    return {"valid": ok, "message": msg}


@app.post("/api/audit")
async def audit(
    file: UploadFile = File(...),
    n_trials: int = Form(...),
    benchmark: Optional[str] = Form(None),
    cost_bps: float = Form(5.0),
) -> dict:
    """Audit an external returns CSV + the declared number of trials tried."""
    raw = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"could not parse CSV: {exc}") from exc
    for c in df.columns:
        if c.lower() in ("date", "timestamp", "time"):
            df = df.drop(columns=[c])
            break
    df = df.select_dtypes(include=[np.number]).dropna(how="all").fillna(0.0)
    if df.shape[1] < 1 or len(df) < 64:
        raise HTTPException(400, "need numeric returns columns with >= 64 rows")
    df.index = pd.RangeIndex(len(df))

    bench = None
    if benchmark and benchmark in SYMBOLS:
        b = load_close(benchmark).pct_change().fillna(0.0)
        bench = b.iloc[-len(df):] if len(b) >= len(df) else None

    analysis = analyze_returns_matrix(df, benchmark_returns=bench,
                                      assumed_cost_bps=cost_bps)
    # rescale DSR to the *declared* trial count (the whole point of auditing)
    if n_trials > df.shape[1]:
        sharpes = np.array([sharpe_ratio(df[c].to_numpy()) for c in df.columns])
        best_col = analysis["best_label"]
        thr = dsr_expected_max_sharpe(sharpes, n_trials=n_trials)
        analysis["dsr"] = psr(df[best_col].to_numpy(), sr_benchmark=thr)
        analysis["dsr_threshold"] = thr
        analysis["n_trials"] = int(n_trials)
    analysis["declared_trials"] = int(n_trials)
    return {"program_id": "audit", "analysis": analysis}


# --- static frontend (single origin) -------------------------------------

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.exists() and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
