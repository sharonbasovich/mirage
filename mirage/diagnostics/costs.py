"""Cost fragility: how much transaction cost the strategy can absorb."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from mirage.diagnostics.sharpe import TRADING_DAYS, sharpe_ratio


@dataclass
class CostFragility:
    cost_grid_bps: np.ndarray
    sharpe_curve: np.ndarray
    breakeven_bps: float  # cost at which Sharpe crosses 0 (capped at grid max)
    assumed_cost_bps: float
    capped: bool = False  # True when the curve never crosses zero on the grid


def cost_fragility(
    gross_returns: np.ndarray,
    turnover: np.ndarray,
    assumed_cost_bps: float = 5.0,
    max_cost_bps: float = 300.0,
    n_points: int = 61,
    periods_per_year: int = TRADING_DAYS,
) -> CostFragility:
    """Sharpe as a function of per-unit-turnover cost in basis points.

    net(c) = gross - c * turnover / 1e4.  Breakeven is the smallest c where
    Sharpe(net(c)) <= 0, found by linear interpolation of the curve.
    """
    g = np.asarray(gross_returns, dtype=float)
    u = np.asarray(turnover, dtype=float)
    grid = np.linspace(0.0, max_cost_bps, n_points)
    curve = np.empty_like(grid)
    for i, c in enumerate(grid):
        curve[i] = sharpe_ratio(g - c * u / 1e4, periods_per_year)

    below = np.where(curve <= 0)[0]
    if len(below) == 0:
        breakeven = float(max_cost_bps)
    else:
        j = int(below[0])
        if j == 0:
            breakeven = 0.0
        else:
            y0, y1 = float(curve[j - 1]), float(curve[j])
            x0, x1 = float(grid[j - 1]), float(grid[j])
            frac = 0.0 if y1 == y0 else (0.0 - y0) / (y1 - y0)
            breakeven = x0 + frac * (x1 - x0)
    return CostFragility(
        cost_grid_bps=grid,
        sharpe_curve=curve,
        breakeven_bps=breakeven,
        assumed_cost_bps=assumed_cost_bps,
        capped=len(below) == 0,
    )
