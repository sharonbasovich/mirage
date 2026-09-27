"""Refresh the cached OHLCV data used by Mirage.

Source: Yahoo Finance via yfinance (free, no API key). Yahoo data is NOT
redistributed with Mirage: this script downloads it into a local, per-user
cache ($MIRAGE_YAHOO_DIR or ~/.cache/mirage/yahoo) for your own research use,
subject to Yahoo's terms (https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).
Requires ``pip install -e ".[data]"``.
"""

from __future__ import annotations

import sys

import pandas as pd
import yfinance as yf

from mirage.data import yahoo_dir

SYMBOLS = {
    # Broad market / macro ETFs
    "SPY": "SPY",
    "QQQ": "QQQ",
    "IWM": "IWM",
    "TLT": "TLT",
    "GLD": "GLD",
    # SPDR sector ETFs
    "XLK": "XLK",
    "XLF": "XLF",
    "XLE": "XLE",
    "XLV": "XLV",
    "XLY": "XLY",
    "XLP": "XLP",
    "XLI": "XLI",
    "XLU": "XLU",
    "XLB": "XLB",
    "XLRE": "XLRE",
    "XLC": "XLC",
    # Crypto
    "BTC-USD": "BTC-USD",
    "ETH-USD": "ETH-USD",
}

START = "2005-01-01"


def main() -> int:
    DATA_DIR = yahoo_dir()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for name, ticker in SYMBOLS.items():
        out = DATA_DIR / f"{name}.csv"
        try:
            df = yf.download(ticker, start=START, progress=False, auto_adjust=True)
            if df.empty:
                raise ValueError("empty frame")
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(how="all")
            df.index.name = "Date"
            df.to_csv(out)
            print(f"{name:8s} {len(df):5d} rows  {df.index[0].date()} -> {df.index[-1].date()}")
        except Exception as exc:  # noqa: BLE001
            failures.append(name)
            print(f"{name:8s} FAILED: {exc}", file=sys.stderr)
    if failures:
        print("failures:", failures, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
