# World Bank Pink Sheet subset

`pinksheet_monthly.csv` holds monthly nominal-USD prices for 15 commodities,
1971-01 → 2026-08. It is extracted unchanged from the "Monthly Prices" sheet of
the official workbook (`CMO-Historical-Data-Monthly.xlsx`, updated
2026-09-02). Rebuild it with `python scripts/fetch_worldbank.py`.

- Source: World Bank Commodity Price Data (The Pink Sheet),
  https://www.worldbank.org/en/research/commodity-markets
- Catalog: https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections
- License: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://datacatalog.worldbank.org/public-licenses
- Attribution: "World Bank Commodity Price Data (The Pink Sheet), World Bank."
- Changes: selected 15 columns, dropped rows before 1971-01 (gold was pegged
  at $35 before then), renamed columns to `WB_*` symbols. Values are unchanged.
