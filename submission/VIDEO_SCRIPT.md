# Mirage demo video script (~3:15)

Shot list + narration. Subtitles in `submission/mirage.srt` mirror the narration
column. Video: 1920x1080 MP4, burned-in English subtitles.

| Time | On screen | Narration / subtitle |
|---|---|---|
| 0:00–0:15 | Title card: "MIRAGE — the backtest lie detector" | "Anyone can build a trading strategy with a three-hundred percent backtest. Almost none survive live. The reason isn't bad code — it's selection bias." |
| 0:15–0:35 | E1 histogram figure (reports/figures/e1_sharpe_histogram.png) | "We ran one thousand random, zero-skill strategies on real S-and-P data. The best backtest looks great — a Sharpe of point six. It's pure luck, and the math knows it." |
| 0:35–1:00 | App opens on Strategy Lab; click "MA Crossover Zoo" preset | "Mirage backtests your strategy grid and — critically — remembers every single trial in a tamper-evident Trial Ledger. Pre-registration for backtests. You can't quietly delete the losers." |
| 1:00–1:35 | Trials run; Verdict page fills: gauge, component table, λ histogram, IS-vs-OOS scatter, cost curve | "Then Mirage runs the academic overfitting battery. The Deflated Sharpe Ratio deflates your best result by how many things you tried. The CSCV test splits history sixteen ways and asks: how often does the in-sample winner underperform? Here — sixty-five percent of the time. This grid is a mirage." |
| 1:35–2:00 | Ledger page: entries table, hash chain, certificate JSON | "Every trial is hash-chained — timestamp, config hash, data hash. Export a pre-registration certificate any third party can verify." |
| 2:00–2:20 | Upload page: drop a CSV, get a verdict | "Already used another backtester? Upload your returns and a trial count — Mirage audits the field, not just its own runs." |
| 2:20–2:45 | E2 ROC + power figures | "And Mirage validates itself. On synthetic markets with planted skill we measured the detector's own error rate — ROC AUC point eight — and publish the curves. A metrology tool that reports its own measurement error." |
| 2:45–3:05 | E3 scorecard figure + verdict recap | "DSR alone misses half of zero-skill zoos — correlated trials break its math. The combined battery misses only five percent. That's why the verdict is a battery, not a number." |
| 3:05–3:15 | End card: repo URL + "not financial advice" | "Mirage — free, open source, MIT licensed. Stop trusting your own backtests." |

## Production notes

- Driven by `scripts/record_demo.py` (Playwright `record_video_dir`), assembled
  with ffmpeg; SRT burned in.
- Keep each UI segment ≥ ~12 s so subtitles are readable.
- Optional narration: `espeak-ng` (free, offline) — subtitles alone are fine.
