"""Market data access.

Two sources, never mixed within one program:

* **World Bank Pink Sheet** (bundled, CC BY 4.0): monthly nominal USD prices
  for 15 commodities, committed under ``data/worldbank/`` so the public demo
  and tests run offline. Rebuild with ``scripts/fetch_worldbank.py``.
* **Yahoo Finance** (user-local, not redistributed): daily ETF/crypto OHLCV
  fetched by each user with ``scripts/fetch_data.py`` into a local cache
  (``$MIRAGE_YAHOO_DIR`` or ``~/.cache/mirage/yahoo``), subject to Yahoo's
  terms of service.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WORLDBANK_CSV = ROOT / "data" / "worldbank" / "pinksheet_monthly.csv"

WORLDBANK_SOURCE = {
    "source": "World Bank Commodity Price Data (The Pink Sheet)",
    "license": "CC BY 4.0",
    "url": "https://datacatalog.worldbank.org/search/dataset/0038238",
    "frequency": "monthly",
}
YAHOO_SOURCE = {
    "source": "Yahoo Finance via yfinance (fetched locally by the user)",
    "license": "Yahoo terms of service; not redistributed with Mirage",
    "url": "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
    "frequency": "daily",
}
PERIODS_PER_YEAR = {"monthly": 12, "daily": 252}

WORLDBANK_SYMBOLS = [
    "WB_GOLD", "WB_SILVER", "WB_PLATINUM", "WB_COPPER", "WB_ALUMINUM",
    "WB_ZINC", "WB_NICKEL", "WB_BRENT", "WB_NATGAS_US", "WB_WHEAT",
    "WB_MAIZE", "WB_SOYBEANS", "WB_SUGAR", "WB_COFFEE", "WB_COTTON",
]

YAHOO_SYMBOLS = [
    "SPY", "QQQ", "IWM", "TLT", "GLD",
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP",
    "XLI", "XLU", "XLB", "XLRE", "XLC",
    "BTC-USD", "ETH-USD",
]

SECTOR_ETFS = [
    "XLK", "XLF", "XLE", "XLV", "XLY", "XLP",
    "XLI", "XLU", "XLB", "XLRE", "XLC",
]


def yahoo_dir() -> Path:
    env = os.environ.get("MIRAGE_YAHOO_DIR")
    return Path(env) if env else Path.home() / ".cache" / "mirage" / "yahoo"


def _yahoo_path(symbol: str) -> Path:
    return yahoo_dir() / f"{symbol}.csv"


def is_available(symbol: str) -> bool:
    if symbol in WORLDBANK_SYMBOLS:
        return WORLDBANK_CSV.exists()
    return symbol in YAHOO_SYMBOLS and _yahoo_path(symbol).exists()


def list_symbols() -> list[str]:
    """Symbols usable right now: bundled World Bank + any locally cached Yahoo."""
    return [s for s in WORLDBANK_SYMBOLS + YAHOO_SYMBOLS if is_available(s)]


def source_info(symbol: str) -> dict[str, str]:
    return dict(WORLDBANK_SOURCE if symbol in WORLDBANK_SYMBOLS else YAHOO_SOURCE)


def frequency(symbols: list[str] | str) -> str:
    """'monthly' or 'daily'; raises ValueError when sources are mixed."""
    syms = [symbols] if isinstance(symbols, str) else list(symbols)
    freqs = {source_info(s)["frequency"] for s in syms}
    if len(freqs) != 1:
        raise ValueError("cannot mix monthly (World Bank) and daily (Yahoo) symbols")
    return freqs.pop()


def periods_per_year(symbols: list[str] | str) -> int:
    return PERIODS_PER_YEAR[frequency(symbols)]


@lru_cache(maxsize=1)
def _worldbank_frame() -> pd.DataFrame:
    df = pd.read_csv(WORLDBANK_CSV, parse_dates=["Date"], index_col="Date")
    return df.sort_index()


def load_ohlcv(symbol: str) -> pd.DataFrame:
    """Price frame with at least a ``Close`` column (World Bank: Close only)."""
    if symbol in WORLDBANK_SYMBOLS:
        s = _worldbank_frame()[symbol].dropna()
        return pd.DataFrame({"Close": s})
    path = _yahoo_path(symbol)
    if symbol not in YAHOO_SYMBOLS or not path.exists():
        raise FileNotFoundError(
            f"no local data for {symbol}; run `python scripts/fetch_data.py` to "
            f"fetch Yahoo data into {yahoo_dir()}"
        )
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    return df.sort_index()


def load_close(symbols: list[str] | str) -> pd.DataFrame | pd.Series:
    """Close prices for one or many symbols, aligned on the union calendar."""
    if isinstance(symbols, str):
        return load_ohlcv(symbols)["Close"]
    frames = {s: load_ohlcv(s)["Close"] for s in symbols}
    return pd.DataFrame(frames).sort_index().ffill().dropna()


def data_hash(symbols: list[str] | None = None) -> str:
    """SHA-256 over the data files backing ``symbols`` (default: all available).

    World Bank symbols hash the bundled CSV plus the symbol name; Yahoo symbols
    hash the user's local CSV, so certificates are bound to the exact bytes used.
    """
    symbols = symbols or list_symbols()
    h = hashlib.sha256()
    wb_bytes: bytes | None = None
    for s in sorted(symbols):
        h.update(s.encode())
        if s in WORLDBANK_SYMBOLS:
            if wb_bytes is None:
                wb_bytes = WORLDBANK_CSV.read_bytes()
            h.update(hashlib.sha256(wb_bytes).digest())
        else:
            h.update(_yahoo_path(s).read_bytes())
    return h.hexdigest()
