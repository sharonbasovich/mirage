"""Strategy framework: declarative specs, param grids, registry."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

# A strategy maps a close-price DataFrame (dates x assets) to a
# target-position DataFrame using only information through each row's date.
PositionFn = Callable[[pd.DataFrame, dict], pd.DataFrame]


@dataclass
class StrategySpec:
    family: str
    params: dict[str, Any] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=list)


@dataclass
class Strategy:
    name: str
    description: str
    position_fn: PositionFn
    default_grid: dict[str, list[Any]]
    default_symbols: list[str]
    long_only_default: bool = True


STRATEGIES: dict[str, Strategy] = {}


def register(s: Strategy) -> Strategy:
    STRATEGIES[s.name] = s
    return s


def build_strategy(name: str) -> Strategy:
    if name not in STRATEGIES:
        raise KeyError(f"unknown strategy family '{name}'; have {sorted(STRATEGIES)}")
    return STRATEGIES[name]


def param_grid(grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Cartesian product of a parameter grid -> list of param dicts."""
    keys = list(grid.keys())
    out = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        out.append(dict(zip(keys, combo)))
    return out


# --- shared indicators ---------------------------------------------------


def rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, float("nan"))
    out = 100 - 100 / (1 + rs)
    return out.fillna(50.0)


def realized_vol(returns: pd.Series, window: int) -> pd.Series:
    import numpy as np

    return returns.rolling(window).std() * np.sqrt(252)
