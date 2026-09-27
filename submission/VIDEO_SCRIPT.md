# Mirage demo video script (2:31)

Final file: `submission/mirage_demo.mp4`, 1920x1080, h264 + AAC Piper TTS
narration (en_US-lessac-medium, offline), burned-in English subtitles
(`submission/mirage.srt`). The narration below is the exact cue text in
`scripts/assemble_video.py`.

| Segment | On screen | Narration / subtitle |
|---|---|---|
| Title | "MIRAGE — the backtest lie detector" | Anyone can build a trading strategy with a three-hundred-percent backtest. Almost none survive live. The reason isn't bad code — it's selection bias. |
| E1 figure | `reports/figures/e1_sharpe_histogram.png` (E1 on user-fetched Yahoo SPY data) | We ran one thousand random, zero-skill strategies on real S&P data. The best backtest looks great — a Sharpe of 0.61. It's pure luck, and the math knows it. |
| Strategy Lab | bundled World Bank universe + Strategy Zoo | Mirage backtests your strategy grid on historical data with realistic costs, and remembers every single trial. |
| Run | click "MA-Crossover Zoo on Gold (monthly, World Bank)" | Every trial lands in a hash-chained Trial Ledger, so the trial count can't quietly shrink inside the ledger. Then the overfitting battery runs: Deflated Sharpe Ratio, CSCV, Reality Check. |
| Verdict | gauge 81, component table, charts | This zoo runs on bundled, openly licensed World Bank gold prices. The overfitting risk is low, twenty-three percent, but the best trial does not beat simply holding gold beyond luck. Reality Check p is point five nine, so the verdict is capped at unclear. |
| Ledger | entries, chain head, unsigned certificate | Every trial is hash-chained — timestamp, config hash, data hash. Export a certificate with the chain head, and publish it to anchor the record. |
| Upload | synthetic returns CSV audit | Already used another backtester? Upload your returns and a trial count — Mirage audits the field, not just its own runs. |
| About | methods + citations | Every method is from the published literature — Deflated Sharpe Ratio, CSCV, White's Reality Check, purged cross-validation — with formulas and citations on the methods page. |
| E2 figure | ROC / power | And Mirage validates itself — planted-skill experiments measure the detector's own ROC AUC at point nine, and the verdict label's own accuracy on ground truth. |
| E3 figure | scorecard | DSR alone misses forty-five percent of zero-skill zoos — the combined battery misses none. The verdict is a battery, not a number. |
| End card | repo URL + disclaimer | Mirage — free, open source, MIT licensed. Stop trusting your own backtests. |

Reproduce: start the API with an empty `MIRAGE_YAHOO_DIR` (public
configuration), then run `python scripts/record_demo.py` and
`python scripts/assemble_video.py`.
