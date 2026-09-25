"""E3 - Report cards for real strategy grids on real data."""

from __future__ import annotations

import json

import numpy as np

from experiments.common import REPORTS, fig, save
from mirage.data import load_close
from mirage.program import analyze_trials, run_program

PROGRAMS: list[tuple[str, str, list[str], dict[str, list], float]] = [
    ("ma_cross_spy", "ma_cross", ["SPY"],
     {"fast": [5, 10, 20, 50], "slow": [50, 100, 150, 200], "long_only": [True]}, 5.0),
    ("tsmom_btc", "tsmom", ["BTC-USD"],
     {"lookback": [7, 14, 21, 63, 126, 189], "long_only": [False, True]}, 15.0),
    ("sector_mom", "sector_mom",
     ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"],
     {"lookback": [63, 126, 189, 252], "skip": [21], "top_k": [2, 3, 4]}, 5.0),
    ("rsi_spy", "rsi_rev", ["SPY"],
     {"window": [5, 10, 14, 21], "low": [20, 30, 40], "high": [60, 70, 80],
      "long_only": [True]}, 5.0),
    ("ml_spy", "ml_daily", ["SPY"],
     {"model": ["gbm"], "n_estimators": [50, 100], "max_depth": [2, 3],
      "learning_rate": [0.05, 0.1], "embargo": [2], "train_window": [504],
      "test_window": [63], "thresh": [0.0], "long_only": [True]}, 5.0),
]


def run() -> dict:
    cards = []
    scatter_done = False
    for name, family, syms, grid, cost in PROGRAMS:
        print(f"=== {name} ===")
        pid, trials = run_program(family, syms, grid=grid, cost_bps=cost)
        bench = load_close("SPY").pct_change().fillna(0.0)
        res = analyze_trials(trials, benchmark_returns=bench, assumed_cost_bps=cost)
        v = res["verdict"]
        cards.append({
            "program": name,
            "program_id": pid,
            "n_trials": res["n_trials"],
            "best_sharpe": res["best_sharpe"],
            "psr": res["psr"],
            "dsr": res["dsr"],
            "pbo": res["pbo"],
            "reality_check_p": res["reality_check_p"],
            "breakeven_bps": res["cost_curve"]["breakeven_bps"],
            "min_btl": res["min_btl"],
            "score": v["score"],
            "label": v["label"],
        })
        print(f"  best Sharpe {res['best_sharpe']:.2f}  DSR p {res['dsr']:.3f}  "
              f"PBO {res['pbo']:.2f}  -> {v['label']} ({v['score']})")

        if not scatter_done:
            scatter_done = True
            f, ax, p = fig("e3_is_vs_oos.png")
            ax.scatter(res["cscv_is_sharpes"], res["cscv_oos_sharpes"],
                       s=8, color="#38bdf8", alpha=0.5)
            ax.axhline(0, color="#f87171", lw=1)
            lim = max(abs(np.array(res["cscv_is_sharpes"])).max(),
                      abs(np.array(res["cscv_oos_sharpes"])).max())
            ax.plot([-lim, lim], [-lim, lim], ":", color="#fbbf24", label="no degradation")
            ax.set_xlabel("in-sample Sharpe of selected config")
            ax.set_ylabel("out-of-sample Sharpe of same config")
            ax.set_title(f"E3: IS-vs-OOS degradation ({name})")
            ax.legend()
            save(f, p)

    f, ax, p = fig("e3_scorecard.png")
    names = [c["program"] for c in cards]
    scores = [c["score"] for c in cards]
    colors = ["#f87171" if c["label"] == "Mirage" else
              "#fbbf24" if c["label"] == "Unclear" else "#34d399" for c in cards]
    ax.barh(names, scores, color=colors)
    for i, c in enumerate(cards):
        ax.text(min(c["score"] + 1, 102), i, f"{c['label']} ({c['score']:.0f})",
                va="center", fontsize=9)
    ax.axvline(40, color="#f87171", ls="--", lw=1)
    ax.axvline(65, color="#34d399", ls="--", lw=1)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Mirage Score")
    ax.set_title("E3: real strategy grids - verdict scorecard")
    save(f, p)

    out = {"experiment": "E3 real strategies", "cards": cards}
    (REPORTS / "e3.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
