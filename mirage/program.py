"""Research-program orchestration: run a grid, log every trial, analyze.

A *program* is one research question (e.g. "MA-crossover on SPY") under
which all parameter trials are recorded in the ledger.  Analysis treats the
whole recorded grid as the multiple-testing universe.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from mirage.backtest import perf_stats, run_backtest
from mirage.data import data_hash, load_close
from mirage.diagnostics.costs import cost_fragility
from mirage.diagnostics.cscv import cscv_pbo
from mirage.diagnostics.haircuts import haircut_adjusted_pvalues
from mirage.diagnostics.reality_check import reality_check
from mirage.diagnostics.sharpe import (
    dsr,
    dsr_expected_max_sharpe,
    min_backtest_length,
    psr,
    sharpe_ratio,
)
from mirage.diagnostics.verdict import build_verdict
from mirage.ledger import Ledger, new_program_id
from mirage.strategies import STRATEGIES, build_strategy, param_grid


@dataclass
class TrialResult:
    label: str
    config: dict
    metrics: dict
    returns: pd.Series
    gross_returns: pd.Series
    turnover: pd.Series
    equity: pd.Series
    entry_id: int


def run_program(
    family: str,
    symbols: list[str],
    grid: dict[str, list[Any]] | None = None,
    cost_bps: float = 5.0,
    slippage_bps: float = 0.0,
    vol_target: float | None = None,
    ledger: Ledger | None = None,
    program_id: str | None = None,
    max_trials: int = 400,
) -> tuple[str, list[TrialResult]]:
    """Run a parameter grid; every trial is appended to the ledger."""
    spec = build_strategy(family)
    grid = grid if grid is not None else spec.default_grid
    combos = param_grid(grid) if grid else [{}]
    # invalid ma_cross combos: fast >= slow
    if family == "ma_cross":
        combos = [c for c in combos if int(c["fast"]) < int(c["slow"])]
    if family == "rsi_rev":
        combos = [c for c in combos if float(c["low"]) < float(c.get("high", 70))]
    combos = combos[:max_trials]

    prices = load_close(symbols)
    if isinstance(prices, pd.Series):
        prices = prices.to_frame()
    dhash = data_hash(symbols)
    ledger = ledger or Ledger()
    program_id = program_id or new_program_id(f"{family}-{symbols[0]}")

    results: list[TrialResult] = []
    for i, params in enumerate(combos):
        pos = spec.position_fn(prices, params)
        bt = run_backtest(prices, pos, cost_bps=cost_bps,
                          slippage_bps=slippage_bps, vol_target=vol_target)
        metrics = perf_stats(bt.returns)
        metrics["n_trades"] = bt.n_trades
        metrics["total_turnover"] = bt.total_turnover
        label = f"{family}[{i}] {json.dumps(params, sort_keys=True)}"
        config = {
            "family": family,
            "symbols": symbols,
            "params": params,
            "cost_bps": cost_bps,
            "slippage_bps": slippage_bps,
            "vol_target": vol_target,
        }
        returns_sha = hashlib.sha256(
            np.ascontiguousarray(bt.returns.to_numpy()).tobytes()
        ).hexdigest()
        entry = ledger.append(program_id, label, config, dhash, metrics, returns_sha)
        results.append(
            TrialResult(
                label=label,
                config=config,
                metrics=metrics,
                returns=bt.returns,
                gross_returns=bt.gross_returns,
                turnover=bt.turnover,
                equity=bt.equity,
                entry_id=entry.id,
            )
        )
    return program_id, results


def analyze_trials(
    trials: list[TrialResult],
    benchmark_returns: pd.Series | None = None,
    assumed_cost_bps: float = 5.0,
    n_blocks: int = 16,
    n_bootstrap: int = 500,
    seed: int = 0,
) -> dict[str, Any]:
    """Full diagnostic battery + Mirage verdict over a set of recorded trials."""
    if not trials:
        raise ValueError("no trials to analyze")

    rets = pd.DataFrame({t.label: t.returns for t in trials}).fillna(0.0)
    trial_sharpes = np.array([sharpe_ratio(rets[c].to_numpy()) for c in rets.columns])
    best_i = int(np.argmax(trial_sharpes))
    best = trials[best_i]

    n_days = int(rets.shape[0])
    best_rets = best.returns.to_numpy()
    best_is_sharpe = float(trial_sharpes[best_i])

    dsr_p = dsr(best_rets, trial_sharpes)
    psr_p = psr(best_rets)
    e_max = dsr_expected_max_sharpe(trial_sharpes)
    min_btl = min_backtest_length(best_rets)

    # per-trial PSR p-values -> multiple-testing haircuts
    pvals = np.array([1 - psr(rets[c].to_numpy()) for c in rets.columns])
    pvals = np.clip(pvals, 1e-12, 1.0)
    haircuts = haircut_adjusted_pvalues(pvals)

    cscv = cscv_pbo(rets.to_numpy(), n_blocks=n_blocks)
    oos_median = float(np.median(cscv.oos_sharpes))

    if benchmark_returns is not None:
        rc = reality_check(
            rets.to_numpy(), benchmark_returns.to_numpy(),
            n_bootstrap=n_bootstrap, seed=seed,
        )
        rc_p = rc.p_value
        rc_best = rc.best_index
    else:
        rc_p, rc_best = None, None

    frag = cost_fragility(
        best.gross_returns.to_numpy(), best.turnover.to_numpy(),
        assumed_cost_bps=assumed_cost_bps,
    )

    verdict = build_verdict(
        dsr_p=dsr_p,
        pbo=cscv.pbo,
        is_sharpe=best_is_sharpe,
        oos_sharpe_median=oos_median,
        breakeven_bps=frag.breakeven_bps,
        assumed_cost_bps=assumed_cost_bps,
        n_days=n_days,
        min_btl=min_btl,
        n_trials=len(trials),
    )

    eq = (1.0 + rets).cumprod()
    return {
        "n_trials": len(trials),
        "n_days": n_days,
        "best_index": best_i,
        "best_label": best.label,
        "best_config": best.config,
        "best_metrics": best.metrics,
        "best_sharpe": best_is_sharpe,
        "trial_sharpes": {c: float(s) for c, s in zip(rets.columns, trial_sharpes)},
        "psr": psr_p,
        "dsr": dsr_p,
        "dsr_threshold": e_max,
        "min_btl": min_btl,
        "haircuts": haircuts,
        "pbo": cscv.pbo,
        "p_oos_loss": cscv.p_oos_loss,
        "degradation_slope": cscv.degradation_slope,
        "cscv_lambdas": cscv.lambdas.tolist(),
        "cscv_is_sharpes": cscv.is_sharpes.tolist(),
        "cscv_oos_sharpes": cscv.oos_sharpes.tolist(),
        "cscv_dominance": cscv.dominance,
        "n_combinations": cscv.n_combinations,
        "reality_check_p": rc_p,
        "reality_check_best": rc_best,
        "cost_curve": {
            "cost_bps": frag.cost_grid_bps.tolist(),
            "sharpe": frag.sharpe_curve.tolist(),
            "breakeven_bps": frag.breakeven_bps,
        },
        "verdict": {
            "score": verdict.score,
            "label": verdict.label,
            "components": [
                {
                    "key": c.key,
                    "label": c.label,
                    "weight": c.weight,
                    "score": round(c.score, 1),
                    "detail": c.detail,
                }
                for c in verdict.components
            ],
            "narrative": verdict.narrative,
        },
        "equity_curves": {
            "dates": [str(d.date()) for d in eq.index],
            "best": eq.iloc[:, best_i].round(4).tolist(),
        },
        "trials": [
            {
                "label": t.label,
                "entry_id": t.entry_id,
                "sharpe": t.metrics.get("sharpe"),
                "ann_return": t.metrics.get("ann_return"),
                "max_drawdown": t.metrics.get("max_drawdown"),
                "n_trades": t.metrics.get("n_trades"),
                "params": t.config.get("params", {}),
            }
            for t in trials
        ],
    }


def analyze_returns_matrix(
    returns: pd.DataFrame,
    benchmark_returns: pd.Series | None = None,
    assumed_cost_bps: float = 5.0,
    n_blocks: int = 16,
    n_bootstrap: int = 500,
    seed: int = 0,
) -> dict[str, Any]:
    """Analyze an externally supplied T x N returns matrix (the audit path).

    Columns are trials; index is a date-like index. Since no turnover data is
    available, the cost-fragility component uses per-column mean |Δreturns|
    approximation only when unknown - instead we run cost fragility on the
    best column with turnover=1 on nonzero days (conservative).
    """
    trials: list[TrialResult] = []
    for col in returns.columns:
        r = returns[col].fillna(0.0)
        metrics = perf_stats(r)
        gross = r.copy()
        # unknown turnover: assume the return stream is net of zero cost and
        # charge the declared cost per nonzero day (turnover=1) for fragility
        turnover = (r != 0).astype(float)
        trials.append(
            TrialResult(
                label=str(col),
                config={"family": "external", "params": {"column": str(col)}},
                metrics=metrics,
                returns=r,
                gross_returns=gross,
                turnover=turnover,
                equity=(1.0 + r).cumprod(),
                entry_id=-1,
            )
        )
    return analyze_trials(
        trials,
        benchmark_returns=benchmark_returns,
        assumed_cost_bps=assumed_cost_bps,
        n_blocks=n_blocks,
        n_bootstrap=n_bootstrap,
        seed=seed,
    )
