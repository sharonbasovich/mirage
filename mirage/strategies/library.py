"""Concrete strategy families."""

from __future__ import annotations

import numpy as np
import pandas as pd

from mirage.strategies.base import Strategy, register, rsi


def _single(prices: pd.DataFrame, series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({prices.columns[0]: series}, index=prices.index)


def ma_cross(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Moving-average crossover: long/short (or long/flat) on SMA cross."""
    fast = int(params["fast"])
    slow = int(params["slow"])
    long_only = bool(params.get("long_only", True))
    close = prices.iloc[:, 0]
    f = close.rolling(fast).mean()
    s = close.rolling(slow).mean()
    sig = (f > s).astype(float)
    if not long_only:
        sig = sig * 2 - 1
    sig[f.isna() | s.isna()] = 0.0
    return _single(prices, sig)


def tsmom(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Time-series momentum: sign of trailing lookback return."""
    lookback = int(params["lookback"])
    long_only = bool(params.get("long_only", False))
    close = prices.iloc[:, 0]
    mom = close / close.shift(lookback) - 1.0
    sig = np.sign(mom)
    if long_only:
        sig = sig.clip(lower=0.0)
    sig[mom.isna()] = 0.0
    return _single(prices, sig)


def sector_mom(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """12-1 style cross-sectional momentum: top-k sector ETFs, equal weight."""
    lookback = int(params.get("lookback", 252))
    skip = int(params.get("skip", 21))
    top_k = int(params.get("top_k", 3))
    mom = prices.shift(skip) / prices.shift(skip + lookback) - 1.0
    rank = mom.rank(axis=1, ascending=False)
    pos = (rank <= top_k).astype(float)
    pos = pos.div(pos.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    pos[mom.isna().all(axis=1)] = 0.0
    return pos


def rsi_rev(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """RSI mean reversion: long when oversold, exit/short when overbought."""
    window = int(params["window"])
    low = float(params["low"])
    high = float(params.get("high", 70))
    long_only = bool(params.get("long_only", True))
    close = prices.iloc[:, 0]
    r = rsi(close, window)
    sig = pd.Series(np.nan, index=prices.index)
    sig[r < low] = 1.0
    sig[r > high] = -1.0 if not long_only else 0.0
    sig = sig.ffill().fillna(0.0)
    return _single(prices, sig)


def bollinger(prices: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Bollinger mean reversion: long below lower band, flat inside, short above."""
    window = int(params["window"])
    k = float(params["k"])
    long_only = bool(params.get("long_only", True))
    close = prices.iloc[:, 0]
    mid = close.rolling(window).mean()
    sd = close.rolling(window).std()
    upper, lower = mid + k * sd, mid - k * sd
    sig = pd.Series(0.0, index=prices.index)
    sig[close < lower] = 1.0
    if not long_only:
        sig[close > upper] = -1.0
    sig[mid.isna()] = 0.0
    return _single(prices, sig)


def buy_hold(prices: pd.DataFrame, params: dict) -> pd.DataFrame:  # noqa: ARG001
    return pd.DataFrame(1.0, index=prices.index, columns=prices.columns)


def _register_all() -> None:
    register(
        Strategy(
            name="ma_cross",
            description="SMA crossover (fast/slow grid) on a single asset",
            position_fn=ma_cross,
            default_grid={
                "fast": [5, 10, 20, 50],
                "slow": [50, 100, 150, 200],
                "long_only": [True],
            },
            default_symbols=["SPY"],
            monthly_grid={"fast": [2, 3, 6], "slow": [9, 12, 18, 24], "long_only": [True]},
            monthly_symbols=["WB_GOLD"],
        )
    )
    register(
        Strategy(
            name="tsmom",
            description="Time-series momentum (lookback grid) on a single asset",
            position_fn=tsmom,
            default_grid={"lookback": [21, 63, 126, 189, 252], "long_only": [False]},
            default_symbols=["SPY"],
            monthly_grid={"lookback": [1, 3, 6, 9, 12], "long_only": [False, True]},
            monthly_symbols=["WB_BRENT"],
        )
    )
    register(
        Strategy(
            name="sector_mom",
            description="Cross-sectional momentum (top-k of a basket; SPDR sectors or commodities)",
            position_fn=sector_mom,
            default_grid={
                "lookback": [126, 189, 252],
                "skip": [21],
                "top_k": [2, 3, 4],
            },
            default_symbols=[
                "XLK",
                "XLF",
                "XLE",
                "XLV",
                "XLY",
                "XLP",
                "XLI",
                "XLU",
                "XLB",
            ],
            monthly_grid={"lookback": [3, 6, 9, 12], "skip": [1], "top_k": [2, 3, 4]},
            monthly_symbols=["WB_GOLD", "WB_SILVER", "WB_COPPER", "WB_ALUMINUM", "WB_BRENT", "WB_WHEAT", "WB_MAIZE", "WB_SOYBEANS"],
        )
    )
    register(
        Strategy(
            name="rsi_rev",
            description="RSI mean reversion (window/threshold grid)",
            position_fn=rsi_rev,
            default_grid={
                "window": [5, 10, 14, 21],
                "low": [20, 30, 40],
                "high": [60, 70, 80],
                "long_only": [True],
            },
            default_symbols=["SPY"],
            monthly_grid={"window": [3, 6, 12], "low": [20, 30, 40], "high": [60, 70, 80],
                          "long_only": [True]},
            monthly_symbols=["WB_GOLD"],
        )
    )
    register(
        Strategy(
            name="bollinger",
            description="Bollinger-band mean reversion",
            position_fn=bollinger,
            default_grid={"window": [10, 20, 40], "k": [1.5, 2.0, 2.5], "long_only": [True]},
            default_symbols=["SPY"],
            monthly_grid={"window": [6, 12, 24], "k": [1.5, 2.0, 2.5], "long_only": [True]},
            monthly_symbols=["WB_GOLD"],
        )
    )
    register(
        Strategy(
            name="buy_hold",
            description="Buy and hold benchmark",
            position_fn=buy_hold,
            default_grid={},
            default_symbols=["SPY"],
            monthly_grid={},
            monthly_symbols=["WB_GOLD"],
        )
    )


_register_all()
