"""Mirage API - FastAPI backend serving the React build (single origin).

Public-deployment hardening:
  * every expensive request is bounded before work starts (symbols, grid
    size, parameter ranges, upload bytes/rows/columns, declared trials);
  * at most ``MIRAGE_MAX_CONCURRENT_RUNS`` backtests/audits run at once,
    extra requests get HTTP 429;
  * program ids are generated server-side and path parameters are checked
    against ``PROGRAM_ID_RE`` and confined to the analysis directory;
  * CORS is off (same-origin only) unless ``MIRAGE_CORS_ORIGINS`` lists
    explicit origins.
"""

from __future__ import annotations

import io
import json
import logging
import math
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from mirage.audit import AuditInputError, prepare_audit_frame
from mirage.data import (
    data_hash,
    frequency,
    is_available,
    list_symbols,
    load_close,
    load_ohlcv,
    source_info,
)
from mirage.ledger import PROGRAM_ID_RE, Ledger, state_dir
from mirage.program import analyze_returns_matrix, analyze_trials, run_program
from mirage.strategies import STRATEGIES

log = logging.getLogger("mirage.api")

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"

# --- limits ----------------------------------------------------------------
MAX_SYMBOLS = 12
MAX_GRID_KEYS = 10
MAX_VALUES_PER_KEY = 12
MAX_TRIALS = 100          # Cartesian grid size accepted by /api/run
MAX_ML_TRIALS = 16        # the ML family refits a model per walk-forward fold
MAX_INT_PARAM = 2000      # rolling windows / lookbacks, in bars
MAX_PARAM_OVERRIDES = {"n_estimators": 300, "max_depth": 6, "top_k": MAX_SYMBOLS}
MAX_COST_BPS = 500.0
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_BODY_BYTES = MAX_UPLOAD_BYTES + 64 * 1024
MAX_AUDIT_ROWS = 10_000
MAX_AUDIT_COLUMNS = 100
MAX_DECLARED_TRIALS = 100_000
MAX_STORED_ANALYSES = 200
MAX_CONCURRENT_RUNS = max(1, int(os.environ.get("MIRAGE_MAX_CONCURRENT_RUNS", "2")))

_run_slots = threading.BoundedSemaphore(MAX_CONCURRENT_RUNS)


def analysis_dir() -> Path:
    d = state_dir() / "analyses"
    d.mkdir(parents=True, exist_ok=True)
    return d


class BodySizeLimit:
    """Reject request bodies above ``max_bytes`` (Content-Length or streamed)."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    too_big = int(v) > self.max_bytes
                except ValueError:
                    too_big = True
                if too_big:
                    await JSONResponse({"detail": "request body too large"},
                                       status_code=413)(scope, receive, send)
                    return
        seen = 0

        async def limited() -> Message:
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > self.max_bytes:
                    raise HTTPException(413, "request body too large")
            return msg

        await self.app(scope, limited, send)


app = FastAPI(title="Mirage", version="0.2.0")
app.add_middleware(BodySizeLimit, max_bytes=MAX_BODY_BYTES)
_cors = [o.strip() for o in os.environ.get("MIRAGE_CORS_ORIGINS", "").split(",") if o.strip()]
if _cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )


@contextmanager
def _run_slot() -> Iterator[None]:
    if not _run_slots.acquire(blocking=False):
        raise HTTPException(429, "server busy: too many concurrent runs, retry shortly",
                            headers={"Retry-After": "5"})
    try:
        yield
    finally:
        _run_slots.release()


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str = Field(max_length=32)
    symbols: list[str] = Field(min_length=1, max_length=MAX_SYMBOLS)
    grid: dict[str, list[Any]] | None = None
    cost_bps: float = Field(5.0, ge=0.0, le=MAX_COST_BPS)
    slippage_bps: float = Field(0.0, ge=0.0, le=MAX_COST_BPS)
    vol_target: float | None = Field(None, gt=0.0, le=2.0)
    benchmark: str | None = Field(None, max_length=16)


WB_BASKET = ["WB_GOLD", "WB_SILVER", "WB_COPPER", "WB_ALUMINUM",
             "WB_BRENT", "WB_WHEAT", "WB_MAIZE", "WB_SOYBEANS"]

DEMO_PRESETS: dict[str, dict[str, Any]] = {
    # bundled World Bank Pink Sheet (CC BY 4.0) - always available
    "wb_gold_ma": {
        "title": "MA-Crossover Zoo on Gold (monthly, World Bank)",
        "family": "ma_cross",
        "symbols": ["WB_GOLD"],
        "benchmark": "WB_GOLD",
        "grid": {"fast": [2, 3, 6], "slow": [9, 12, 18, 24], "long_only": [True]},
        "cost_bps": 5.0,
    },
    "wb_brent_tsmom": {
        "title": "TS-Momentum Grid on Brent Crude (monthly, World Bank)",
        "family": "tsmom",
        "symbols": ["WB_BRENT"],
        "benchmark": "WB_BRENT",
        "grid": {"lookback": [1, 3, 6, 9, 12], "long_only": [False, True]},
        "cost_bps": 10.0,
    },
    "wb_commodity_mom": {
        "title": "Commodity Cross-Sectional Momentum (monthly, World Bank)",
        "family": "sector_mom",
        "symbols": WB_BASKET,
        "grid": {"lookback": [3, 6, 9, 12], "skip": [1], "top_k": [2, 3, 4]},
        "cost_bps": 10.0,
    },
    "wb_gold_rsi": {
        "title": "RSI Mean-Reversion Zoo on Gold (monthly, World Bank)",
        "family": "rsi_rev",
        "symbols": ["WB_GOLD"],
        "benchmark": "WB_GOLD",
        "grid": {"window": [3, 6, 12], "low": [20, 30, 40], "high": [60, 70, 80],
                 "long_only": [True]},
        "cost_bps": 5.0,
    },
    # user-local Yahoo cache (scripts/fetch_data.py) - listed only when present
    "ma_zoo": {
        "title": "MA-Crossover Zoo on SPY",
        "family": "ma_cross",
        "symbols": ["SPY"],
        "benchmark": "SPY",
        "grid": {"fast": [5, 10, 20, 50], "slow": [50, 100, 150, 200], "long_only": [True]},
        "cost_bps": 5.0,
    },
    "btc_tsmom": {
        "title": "TS-Momentum Grid on BTC-USD",
        "family": "tsmom",
        "symbols": ["BTC-USD"],
        "benchmark": "BTC-USD",
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
        "benchmark": "SPY",
        "grid": {"window": [5, 10, 14, 21], "low": [20, 30, 40], "high": [60, 70, 80],
                 "long_only": [True]},
        "cost_bps": 5.0,
    },
    "ml_spy": {
        "title": "ML Direction Predictor on SPY",
        "family": "ml_daily",
        "symbols": ["SPY"],
        "benchmark": "SPY",
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


# --- validation --------------------------------------------------------------

def _check_program_id(program_id: str) -> str:
    if not PROGRAM_ID_RE.fullmatch(program_id):
        raise HTTPException(400, "invalid program id")
    return program_id


def _analysis_path(program_id: str) -> Path:
    base = analysis_dir().resolve()
    p = (base / f"{_check_program_id(program_id)}.json").resolve()
    if p.parent != base:
        raise HTTPException(400, "invalid program id")
    return p


def _save_analysis(program_id: str, analysis: dict) -> None:
    _analysis_path(program_id).write_text(json.dumps(analysis))
    stored = sorted(analysis_dir().glob("*.json"), key=lambda f: f.stat().st_mtime)
    for old in stored[:-MAX_STORED_ANALYSES]:
        old.unlink(missing_ok=True)


def _load_analysis(program_id: str) -> dict | None:
    p = _analysis_path(program_id)
    if p.exists():
        return json.loads(p.read_text())
    return None


def _check_value(key: str, v: Any) -> None:
    if isinstance(v, bool):
        return
    if isinstance(v, int | float):
        if not math.isfinite(v):
            raise HTTPException(400, f"grid value for {key!r} must be finite")
        cap = MAX_PARAM_OVERRIDES.get(key, MAX_INT_PARAM)
        if not -cap <= v <= cap:
            raise HTTPException(400, f"grid value for {key!r} out of range (|x| <= {cap})")
        return
    if isinstance(v, str) and len(v) <= 16:
        return
    raise HTTPException(400, f"unsupported grid value for {key!r}")


def validate_run(req: RunRequest) -> tuple[dict[str, list[Any]] | None, str]:
    """Bounds-check a run before any backtest work; returns (grid, frequency)."""
    if req.family not in STRATEGIES:
        raise HTTPException(400, "unknown strategy family")
    if len(set(req.symbols)) != len(req.symbols):
        raise HTTPException(400, "duplicate symbols")
    missing = [s for s in req.symbols if not is_available(s)]
    if missing:
        raise HTTPException(400, f"unavailable symbols: {missing[:MAX_SYMBOLS]}")
    try:
        freq = frequency(req.symbols)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    spec = STRATEGIES[req.family]
    template = spec.monthly_grid if freq == "monthly" else spec.default_grid
    if template is None:
        raise HTTPException(400, f"{req.family} is not available for {freq} data")
    grid = req.grid if req.grid is not None else template
    if len(grid) > MAX_GRID_KEYS:
        raise HTTPException(400, f"grid has more than {MAX_GRID_KEYS} parameters")
    unknown = sorted(set(grid) - set(spec.default_grid))
    if unknown:
        raise HTTPException(400, f"unknown grid parameters: {unknown[:MAX_GRID_KEYS]}")
    n = 1
    for k, vals in grid.items():
        if not vals:
            raise HTTPException(400, f"grid parameter {k!r} has no values")
        if len(vals) > MAX_VALUES_PER_KEY:
            raise HTTPException(400, f"grid parameter {k!r} has more than "
                                     f"{MAX_VALUES_PER_KEY} values")
        for v in vals:
            _check_value(k, v)
        n *= len(vals)
    cap = MAX_ML_TRIALS if req.family == "ml_daily" else MAX_TRIALS
    if n > cap:
        raise HTTPException(413, f"grid expands to {n} trials; the limit is {cap}")
    if req.benchmark is not None:
        if not is_available(req.benchmark):
            raise HTTPException(400, "unavailable benchmark")
        if source_info(req.benchmark)["frequency"] != freq:
            raise HTTPException(400, "benchmark frequency must match the symbols")
    return grid, freq


def _benchmark(req: RunRequest, freq: str) -> pd.Series | None:
    if req.benchmark:
        return load_close(req.benchmark).pct_change().fillna(0.0)
    if freq == "daily":
        return load_close("SPY").pct_change().fillna(0.0) if is_available("SPY") else None
    # monthly default: equal-weight buy-and-hold of the program's own assets
    px = load_close(req.symbols)
    if isinstance(px, pd.Series):
        px = px.to_frame()
    return px.pct_change().fillna(0.0).mean(axis=1)


# --- routes ------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "data_hash": data_hash()[:16]}


@app.get("/api/symbols")
def symbols() -> list[dict]:
    out = []
    for s in list_symbols():
        df = load_ohlcv(s)
        info = source_info(s)
        out.append({
            "symbol": s,
            "rows": int(len(df)),
            "start": str(df.index[0].date()),
            "end": str(df.index[-1].date()),
            "frequency": info["frequency"],
            "source": info["source"],
            "license": info["license"],
        })
    return out


@app.get("/api/strategies")
def strategies() -> list[dict]:
    daily = any(not s.startswith("WB_") for s in list_symbols())
    out = []
    for s in STRATEGIES.values():
        use_daily = daily and all(is_available(x) for x in s.default_symbols)
        if use_daily:
            grid, syms = s.default_grid, s.default_symbols
        elif s.monthly_grid is not None and s.monthly_symbols:
            grid, syms = s.monthly_grid, s.monthly_symbols
        else:
            continue
        out.append({"name": s.name, "description": s.description,
                    "default_grid": grid, "default_symbols": syms})
    return out


@app.get("/api/demos")
def demos() -> list[dict]:
    return [{"key": k, "title": v["title"], "family": v["family"],
             "symbols": v["symbols"], "grid": v["grid"], "cost_bps": v["cost_bps"]}
            for k, v in DEMO_PRESETS.items()
            if all(is_available(s) for s in v["symbols"])]


@app.get("/api/programs")
def programs() -> list[dict]:
    progs = Ledger().programs()
    for p in progs:
        pid = p["program_id"]
        p["has_analysis"] = bool(PROGRAM_ID_RE.fullmatch(pid)) and _load_analysis(pid) is not None
    return progs


@app.post("/api/run")
def run(req: RunRequest) -> dict:
    grid, freq = validate_run(req)
    with _run_slot():
        try:
            pid, trials = run_program(
                req.family, req.symbols, grid=grid,
                cost_bps=req.cost_bps, slippage_bps=req.slippage_bps,
                vol_target=req.vol_target, max_trials=MAX_TRIALS,
            )
            if not trials:
                raise HTTPException(400, "grid produced no valid trials")
            analysis = analyze_trials(trials, benchmark_returns=_benchmark(req, freq),
                                      assumed_cost_bps=req.cost_bps)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            log.exception("run failed")
            raise HTTPException(500, "backtest failed") from exc
    _save_analysis(pid, analysis)
    return {"program_id": pid, "analysis": analysis}


@app.post("/api/demo/{key}")
def run_demo(key: str) -> dict:
    p = DEMO_PRESETS.get(key)
    if p is None or not all(is_available(s) for s in p["symbols"]):
        raise HTTPException(404, "unknown demo")
    return run(RunRequest(
        family=p["family"], symbols=p["symbols"], grid=p["grid"],
        cost_bps=p["cost_bps"], slippage_bps=0.0, vol_target=None, benchmark=p.get("benchmark"),
    ))


@app.get("/api/programs/{program_id}/analysis")
def program_analysis(program_id: str) -> dict:
    a = _load_analysis(program_id)
    if a is None:
        raise HTTPException(404, "no stored analysis for program (run it first)")
    return a


@app.get("/api/programs/{program_id}/trials")
def program_trials(program_id: str) -> list[dict]:
    entries = Ledger().entries(_check_program_id(program_id))
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
    entries = led.entries(_check_program_id(program_id))
    if not entries:
        raise HTTPException(404, "unknown program")
    analysis = _load_analysis(program_id)
    cert = led.export_certificate(program_id, verdict=(analysis or {}).get("verdict"))
    cert["data_hash"] = entries[-1].data_hash
    return cert


@app.get("/api/ledger/verify")
def ledger_verify() -> dict:
    ok, msg = Ledger().verify_chain()
    return {"valid": ok, "message": msg}


async def _read_bounded(file: UploadFile, limit: int) -> bytes:
    buf = bytearray()
    while chunk := await file.read(64 * 1024):
        buf.extend(chunk)
        if len(buf) > limit:
            raise HTTPException(413, f"upload exceeds {limit // (1024 * 1024)} MiB")
    return bytes(buf)


@app.post("/api/audit")
async def audit(
    file: UploadFile = File(...),
    n_trials: int = Form(..., ge=1, le=MAX_DECLARED_TRIALS),
    benchmark: str | None = Form(None, max_length=16),
    cost_bps: float = Form(5.0, ge=0.0, le=MAX_COST_BPS),
    frequency_: str = Form("daily", alias="frequency", pattern="^(daily|monthly)$"),
) -> dict:
    """Audit an external returns CSV + the declared number of trials tried."""
    raw = await _read_bounded(file, MAX_UPLOAD_BYTES)
    with _run_slot():
        try:
            df = pd.read_csv(io.BytesIO(raw), nrows=MAX_AUDIT_ROWS + 1)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, "could not parse CSV") from exc
        if len(df) > MAX_AUDIT_ROWS:
            raise HTTPException(413, f"more than {MAX_AUDIT_ROWS} rows")
        if df.shape[1] > MAX_AUDIT_COLUMNS + 1:
            raise HTTPException(413, f"more than {MAX_AUDIT_COLUMNS} return columns")
        try:
            prep = prepare_audit_frame(
                df, declared_trials=n_trials, frequency=frequency_,
                benchmark=benchmark,
            )
        except AuditInputError as exc:
            raise HTTPException(400, str(exc)) from exc
        if prep.returns.shape[1] > MAX_AUDIT_COLUMNS:
            raise HTTPException(413, f"more than {MAX_AUDIT_COLUMNS} return columns")
        ppy = 12 if frequency_ == "monthly" else 252

        try:
            analysis = analyze_returns_matrix(
                prep.returns, benchmark_returns=prep.benchmark,
                assumed_cost_bps=cost_bps, periods_per_year=ppy,
                declared_trials=n_trials,
                frequency_verified=prep.has_dates,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            log.exception("audit failed")
            raise HTTPException(500, "audit failed") from exc
        if prep.benchmark_dropped:
            analysis["benchmark_dropped_rows"] = prep.benchmark_dropped
    return {"program_id": "audit", "analysis": analysis}


# --- static frontend (single origin) -------------------------------------

if FRONTEND_DIST.exists():
    _dist = FRONTEND_DIST.resolve()
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(404, "not found")
        # index.html must not be cached: hashed /assets filenames change per build.
        headers = {"Cache-Control": "no-cache"}
        candidate = (_dist / full_path).resolve()
        if (full_path and candidate.is_relative_to(_dist)
                and candidate.exists() and candidate.is_file()):
            return FileResponse(candidate, headers=headers)
        return FileResponse(_dist / "index.html", headers=headers)

