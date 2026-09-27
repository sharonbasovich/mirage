# World Bank Pink Sheet subset

`pinksheet_monthly.csv` holds monthly nominal-USD prices for 15 commodities,
1971-01 → 2026-08. It is a transformed subset of the "Monthly Prices" sheet
of the official workbook (`CMO-Historical-Data-Monthly.xlsx`, updated
2026-09-02). Rebuild it with `python scripts/fetch_worldbank.py`.

- Source: World Bank Commodity Price Data (The Pink Sheet),
  https://www.worldbank.org/en/research/commodity-markets
- Catalog: https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections
- License: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://datacatalog.worldbank.org/public-licenses
- Attribution: "World Bank Commodity Price Data (The Pink Sheet), World Bank."
- Changes (transformations): converted the Excel sheet to CSV, selected 15
  commodity columns, dropped rows before 1971-01 (gold was pegged at $35
  before then), and renamed columns to `WB_*` symbols. The numeric price
  values are preserved as published.

These are monthly reference/spot prices, not an investable return series or
executable bars. Backtests on them in Mirage are hypothetical price-series
illustrations of the diagnostics, not realizable trading P&L; futures roll,
storage, financing and execution details are not modeled.
