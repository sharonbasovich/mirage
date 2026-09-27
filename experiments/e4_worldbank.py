"""E4 - Report cards on the bundled, CC BY 4.0 World Bank monthly commodity data.

Fully offline and redistributable: this is the reproducible public demo.
Source: World Bank Commodity Price Data (The Pink Sheet), CC BY 4.0.
"""

from __future__ import annotations

import json

import pandas as pd

from experiments.common import REPORTS, fig, save
from mirage.api import DEMO_PRESETS
from mirage.data import load_close
from mirage.program import analyze_trials, run_program

PROGRAMS = ["wb_gold_ma", "wb_brent_tsmom", "wb_commodity_mom", "wb_gold_rsi"]


def run() -> dict:
    cards = []
    for key in PROGRAMS:
        p = DEMO_PRESETS[key]
        print(f"=== {key} ===")
        pid, trials = run_program(p["family"], p["symbols"], grid=p["grid"],
                                  cost_bps=p["cost_bps"])
        px = load_close(p["symbols"])
        if isinstance(px, pd.Series):
            px = px.to_frame()
        bench = px.pct_change().fillna(0.0).mean(axis=1)  # equal-weight buy & hold
        res = analyze_trials(trials, benchmark_returns=bench, assumed_cost_bps=p["cost_bps"])
        v = res["verdict"]
        cards.append({
            "program": key,
            "program_id": pid,
            "n_trials": res["n_trials"],
            "n_months": res["n_days"],
            "best_sharpe": res["best_sharpe"],
            "psr": res["psr"],
            "dsr": res["dsr"],
            "pbo": res["pbo"],
            "reality_check_p": res["reality_check_p"],
            "min_btl_months": res["min_btl"],
            "score": v["score"],
            "label": v["label"],
        })
        print(f"  best Sharpe {res['best_sharpe']:.2f}  DSR p {res['dsr']:.3f}  "
              f"PBO {res['pbo']:.2f}  RC p {res['reality_check_p']:.2f} "
              f"-> {v['label']} ({v['score']})")

    f, ax, path = fig("e4_worldbank_scorecard.png")
    colors = ["#f87171" if c["label"] == "Mirage" else
              "#fbbf24" if c["label"] == "Unclear" else "#34d399" for c in cards]
    ax.barh([c["program"] for c in cards], [c["score"] for c in cards], color=colors)
    for i, c in enumerate(cards):
        ax.text(c["score"] + 1, i, f"{c['label']} ({c['score']:.0f})", va="center")
    ax.set_xlim(0, 110)
    ax.set_xlabel("Mirage Score (0-100)")
    ax.set_title("E4: World Bank monthly commodities (CC BY 4.0)")
    save(f, path)
    out = {"source": "World Bank Commodity Price Data (The Pink Sheet), CC BY 4.0",
           "cards": cards}
    (REPORTS / "e4.json").write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    run()
