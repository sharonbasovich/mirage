"""Cached market data access.

All prices come from CSVs committed under ``data/`` (fetched from Yahoo
Finance via ``scripts/fetch_data.py``), so the whole project runs offline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SYMBOLS = [
    "SPY",
    "QQQ",
    "IWM",
    "TLT",
    "GLD",
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLY",
    "XLP",
    "XLI",
    "XLU",
    "XLB",
    "XLRE",
    "XLC",
    "BTC-USD",
    "ETH-USD",
]

SECTOR_ETFS = [
    "XLK",
    "XLF",
    "XLE",
    "XLV",
    "XLY",
    "XLP",
    "XLI",
    "XLU",
    "XLB",
    "XLRE",
    "XLC",
]


def list_symbols() -> list[str]:
    return sorted(p.stem for p in DATA_DIR.glob("*.csv"))


def load_ohlcv(symbol: str) -> pd.DataFrame:
    path = DATA_DIR / f"{symbol}.csv"
    if not path.exists():
        raise FileNotFoundError(f"no cached data for {symbol} ({path})")
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    return df.sort_index()


def load_close(symbols: list[str] | str) -> pd.DataFrame | pd.Series:
    """Close prices for one or many symbols, aligned on the union calendar."""
    if isinstance(symbols, str):
        return load_ohlcv(symbols)["Close"]
    frames = {s: load_ohlcv(s)["Close"] for s in symbols}
    return pd.DataFrame(frames).sort_index().ffill().dropna()


def data_hash(symbols: list[str] | None = None) -> str:
    """SHA-256 over the cached CSVs (sorted by name) — embedded in ledger entries."""
    symbols = symbols or SYMBOLS
    h = hashlib.sha256()
    for s in sorted(symbols):
        path = DATA_DIR / f"{s}.csv"
        h.update(path.read_bytes())
    return h.hexdigest()
