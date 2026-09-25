"""Vectorized daily backtester with strict no-lookahead.

Convention: a signal/position generated from data through close of day t is
executed at close of day t (positions are shifted forward one day), so the
position on day t earns the close-to-close return of day t only if it was
decided by data available through day t-1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class BacktestResult:
    returns: pd.Series  # net daily strategy returns
    gross_returns: pd.Series
    positions: pd.DataFrame  # post-shift weights per asset
    turnover: pd.Series
    equity: pd.Series
    n_trades: int
    total_turnover: float
    meta: dict = field(default_factory=dict)


def run_backtest(
    prices: pd.DataFrame,
    target_positions: pd.DataFrame,
    cost_bps: float = 5.0,
    slippage_bps: float = 0.0,
    vol_target: float | None = None,
    vol_window: int = 20,
) -> BacktestResult:
    """Backtest a target-position schedule.

    Parameters
    ----------
    prices : DataFrame
        Close prices, dates x assets.
    target_positions : DataFrame
        Weights decided using information through each row's date (same index
        as prices, subset allowed). Values in [-1, 1] per asset typically.
    cost_bps : float
        Transaction cost per unit of one-way turnover, in basis points.
    slippage_bps : float
        Extra slippage charged per unit of turnover, in basis points.
    vol_target : float | None
        Annualized volatility target. Positions are scaled by
        target/realized_vol (realized from past returns only).
    """
    prices = prices.sort_index()
    pos = target_positions.reindex(prices.index).fillna(0.0)
    pos = pos.reindex(columns=prices.columns).fillna(0.0)

    rets = prices.pct_change().fillna(0.0)

    # No-lookahead: positions decided at close t apply from t+1.
    pos_exec = pos.shift(1).fillna(0.0)

    if vol_target is not None:
        realized = rets.std(axis=1) * np.sqrt(TRADING_DAYS)
        realized = realized.replace(0.0, np.nan).shift(1)
        scale = (vol_target / realized).clip(upper=3.0).fillna(0.0)
        pos_exec = pos_exec.mul(scale, axis=0)

    gross = (pos_exec * rets).sum(axis=1)

    turnover = pos_exec.diff().abs().sum(axis=1)
    turnover.iloc[0] = pos_exec.iloc[0].abs().sum()

    drag = turnover * (cost_bps + slippage_bps) / 1e4
    net = gross - drag

    equity = (1.0 + net).cumprod()
    n_trades = int((turnover > 1e-9).sum())

    return BacktestResult(
        returns=net,
        gross_returns=gross,
        positions=pos_exec,
        turnover=turnover,
        equity=equity,
        n_trades=n_trades,
        total_turnover=float(turnover.sum()),
    )


def perf_stats(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> dict:
    r = returns.dropna()
    if len(r) < 2:
        return {"sharpe": 0.0, "ann_return": 0.0, "ann_vol": 0.0, "max_drawdown": 0.0, "days": int(len(r))}
    mu = float(r.mean())
    sd = float(r.std(ddof=1))
    sharpe = mu / sd * np.sqrt(periods_per_year) if sd > 0 else 0.0
    ann_ret = float((1.0 + r).prod() ** (periods_per_year / len(r)) - 1.0)
    eq = (1.0 + r).cumprod()
    dd = float((eq / eq.cummax() - 1.0).min())
    return {
        "sharpe": sharpe,
        "ann_return": ann_ret,
        "ann_vol": float(sd * np.sqrt(periods_per_year)),
        "max_drawdown": dd,
        "days": int(len(r)),
    }
