# Mirage demo video script (3:03)

Generated from `scripts/assemble_video.py`; subtitles in `submission/mirage.srt` are identical to the narration. Narration: Piper TTS (`en_US-lessac-medium`, offline). Submitted evidence is E2 (synthetic) and E4 (bundled World Bank Pink Sheet, CC BY 4.0) only; no Yahoo-derived data, figures or numbers appear in the video.

| Time | Segment | On screen | Narration / subtitle |
|---|---|---|---|
| 00:00 | Title card | MIRAGE, tagline, GIBC V2 Track 02, data: World Bank Pink Sheet (CC BY 4.0) + synthetic series | Try fifty parameter combinations, keep the best one, and part of that winning backtest is luck. That is selection bias, and Mirage is built to measure it. |
| 00:12 | Strategy Lab | Lab page, World Bank symbols, Strategy Zoo presets, data note | Mirage backtests a whole strategy grid on historical data with transaction costs. The bundled data is the World Bank Pink Sheet: monthly commodity reference prices, licensed CC BY 4.0. These are hypothetical price-series backtests, not realizable trading profits. |
| 00:29 | World Bank run | Click "MA-Crossover Zoo on Gold (monthly, World Bank)", 12 trials run | One click runs twelve moving-average crossover trials on gold. Every trial is appended to a hash-chained Trial Ledger, and the diagnostics use that full trial count: Deflated Sharpe Ratio, CSCV, and White's Reality Check. |
| 00:44 | Verdict | Score 81 Unclear; component table; DSR confidence 100.0% ("not P(skill)"); PBO 23.2%; RC p 0.59; plain-English read | The best trial has a Sharpe of 0.71, and a deflated Sharpe confidence of 1.00. That is an exceedance estimate over the best-of-twelve luck threshold, not the probability of genuine skill. Overfitting risk is low: PBO is 23 percent. But the Reality Check p-value against holding gold is 0.59, so there is insufficient evidence of outperformance. The verdict is capped at Unclear, with a score of 81. |
| 01:11 | Trial Ledger | 12 entries, chain intact, unsigned certificate | Each ledger entry hashes its timestamp, config, data hash, and the previous entry. That detects edits or deletions within an intact ledger. The chain is not signed or externally anchored, so the exported certificate is unsigned. |
| 01:26 | Upload audit | Synthetic returns CSV with declared trial count, audit verdict | Already using another backtester? Upload a returns CSV, here a set of synthetic strategies, with a declared trial count, and Mirage runs the same audit. |
| 01:37 | About / Methods | Formulas and citations; DSR confidence and Reality Check wording | Every method comes from the academic literature, with formulas and citations on the methods page. |
| 01:48 | E2 power | reports/figures/e2_power.png | Does the detector work? In experiment E2 we plant known skill in one of fifty synthetic strategies. When the skilled strategy wins in-sample, the verdict says Survives 82.5 percent of the time at a true Sharpe of 1.5, and 97.5 percent at 2.0. |
| 02:06 | E2 ROC | reports/figures/e2_roc.png | On pure-noise zoos, the label says Survives only 5 percent of the time, while a DSR confidence above 0.5 alone would flag 57.5 percent. Across 320 synthetic zoos the label is right 82 percent of the time. ROC AUC is 0.91 for DSR and 0.90 for PBO. |
| 02:27 | E4 scorecard | reports/figures/e4_worldbank_scorecard.png | Experiment E4 runs four hypothetical zoos on the bundled World Bank prices: gold crossover, Brent momentum, commodity momentum, and gold RSI. None shows sufficient evidence of beating its benchmark after data snooping, so all four are Unclear, with scores from 52 to 87. Futures roll, storage, and financing are not modeled. |
| 02:50 | End card | repo URL, World Bank CC BY 4.0 attribution, historical simulation only, not financial advice | Mirage is free, open source, and MIT licensed. Data: World Bank Pink Sheet, CC BY 4.0. It is a historical-simulation research prototype, not financial advice. |

## Accuracy notes

- DSR is shown as a model-based confidence (exceedance) estimate, not a p-value and not the probability that genuine skill exists.
- Reality Check p = 0.59 means insufficient evidence of outperformance versus buy-and-hold gold; it does not prove there is no edge.
- E4 uses monthly Pink Sheet reference/spot prices, not an investable return series or executable bars. The backtests are hypothetical price-series illustrations, not realizable trading P&L; futures roll, storage, financing and execution are not modeled.
- The ledger hash chain detects edits or deletions within an intact ledger. It is unsigned and not externally anchored, and no chain head has been published.
- Historical simulation only. Research prototype, not financial advice.

## Reproduce

```bash
pip install -e ".[dev]"
python -m experiments.run_all e2 && python -m experiments.run_all e4   # figures
(cd frontend && npm ci && npm run build)
MIRAGE_YAHOO_DIR=/tmp/empty uvicorn mirage.api:app --port 8000 &    # World Bank data only
python scripts/record_demo.py      # Playwright screen capture + screenshots
python scripts/assemble_video.py   # Piper narration, SRT, burned subtitles -> submission/mirage_demo.mp4
```
