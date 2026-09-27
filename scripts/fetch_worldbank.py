"""Rebuild the bundled World Bank Pink Sheet subset used by Mirage.

Source: World Bank Commodity Price Data ("The Pink Sheet"), monthly prices in
nominal US dollars. https://www.worldbank.org/en/research/commodity-markets
Dataset: https://datacatalog.worldbank.org/search/dataset/0038238
License: Creative Commons Attribution 4.0 International (CC BY 4.0).
Attribution: "World Bank Commodity Price Data (The Pink Sheet)", World Bank.

The resulting CSV (``data/worldbank/pinksheet_monthly.csv``) is committed so the
public demo runs offline. Requires ``pip install -e ".[data]"`` (openpyxl).
"""

from __future__ import annotations

import io
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

URL = (
    "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/"
    "related/CMO-Historical-Data-Monthly.xlsx"
)
OUT = Path(__file__).resolve().parent.parent / "data" / "worldbank" / "pinksheet_monthly.csv"
START = "1971-01-01"  # post-Bretton Woods: gold was fixed at $35 before 1971

COLUMNS = {
    "WB_GOLD": "Gold",
    "WB_SILVER": "Silver",
    "WB_PLATINUM": "Platinum",
    "WB_COPPER": "Copper",
    "WB_ALUMINUM": "Aluminum",
    "WB_ZINC": "Zinc",
    "WB_NICKEL": "Nickel",
    "WB_BRENT": "Crude oil, Brent",
    "WB_NATGAS_US": "Natural gas, US",
    "WB_WHEAT": "Wheat, US HRW",
    "WB_MAIZE": "Maize",
    "WB_SOYBEANS": "Soybeans",
    "WB_SUGAR": "Sugar, world",
    "WB_COFFEE": "Coffee, Arabica",
    "WB_COTTON": "Cotton, A Index",
}


def main(src: str | None = None) -> None:
    if src:
        raw = Path(src).read_bytes()
    else:
        with urllib.request.urlopen(URL, timeout=60) as resp:  # noqa: S310
            raw = resp.read()
    sheet = pd.read_excel(io.BytesIO(raw), sheet_name="Monthly Prices", header=4)
    sheet = sheet.rename(columns={sheet.columns[0]: "month"})
    sheet = sheet[sheet["month"].astype(str).str.match(r"^\d{4}M\d{2}$")]
    headers = {str(c).strip(): c for c in sheet.columns}
    out = pd.DataFrame(
        {"Date": pd.to_datetime(sheet["month"].str.replace("M", "-") + "-01")}
    )
    for sym, col in COLUMNS.items():
        out[sym] = pd.to_numeric(sheet[headers[col]].replace("…", np.nan), errors="coerce")
    out = out[out["Date"] >= START].dropna(how="all", subset=list(COLUMNS))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, float_format="%.4f")
    print(f"wrote {OUT} ({len(out)} months, {out['Date'].min().date()} .. "
          f"{out['Date'].max().date()})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
