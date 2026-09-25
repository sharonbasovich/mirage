"""E1 - False-positive rate.

1,000 random zero-skill strategies on real SPY returns: the best in-sample
Sharpe looks great but the diagnostics must flag it.  We then measure the
detector's false-positive rate at standard thresholds over repeated
independent zoos - including the full Mirage verdict label.
"""

from __future__ import annotations

import json

import numpy as np

from experiments.common import REPORTS, fig, random_signal_matrix, save
from mirage.data import load_close
from mirage.diagnostics.costs import cost_fragility
from mirage.diagnostics.cscv import cscv_pbo
from mirage.diagnostics.reality_check import reality_check
from mirage.diagnostics.sharpe import (
    dsr,
    dsr_expected_max_sharpe,
    min_backtest_length,
    psr,
    sharpe_ratio,
)
from mirage.diagnostics.verdict import build_verdict


def _zoo_verdict(m: np.ndarray, bench: np.ndarray, assumed_cost_bps: float = 5.0):
    """Full Mirage verdict over one returns matrix (same inputs as analyze)."""
    sharpes = np.array([sharpe_ratio(m[:, i]) for i in range(m.shape[1])])
    bi = int(np.argmax(sharpes))
    cscv = cscv_pbo(m, n_blocks=8)
    rc = reality_check(m, bench, n_bootstrap=200, seed=0)
    # unknown turnover on an external matrix: charge cost per nonzero day
    frag = cost_fragility(m[:, bi], (m[:, bi] != 0).astype(float),
                          assumed_cost_bps=assumed_cost_bps)
    v = build_verdict(
        dsr_p=dsr(m[:, bi], sharpes),
        pbo=cscv.pbo,
        is_sharpe=float(np.median(cscv.is_sharpes)),
        oos_sharpe_median=float(np.median(cscv.oos_sharpes)),
        breakeven_bps=frag.breakeven_bps,
        assumed_cost_bps=assumed_cost_bps,
        n_days=m.shape[0],
        min_btl=min_backtest_length(m[:, bi]),
        n_trials=m.shape[1],
        rc_p=rc.p_value,
        breakeven_capped=frag.capped,
    )
    return v, cscv, rc, sharpes, bi


def run(n_zoo: int = 1000, n_reps: int = 20, rep_size: int = 100, seed: int = 7) -> dict:
    spy = load_close("SPY").pct_change().dropna().to_numpy()

    # --- headline: one big random zoo on real data ---------------------------
    m = random_signal_matrix(spy, n_zoo, seed=seed)
    sharpes = np.array([sharpe_ratio(m[:, i]) for i in range(m.shape[1])])
    best_i = int(np.argmax(sharpes))
    thr = dsr_expected_max_sharpe(sharpes)
    dsr_p = dsr(m[:, best_i], sharpes)
    psr_p = psr(m[:, best_i])
    sub = np.random.default_rng(seed).choice(m.shape[1], 200, replace=False)
    pbo = cscv_pbo(m[:, sub], n_blocks=16).pbo
    verdict, _, rc, _, _ = _zoo_verdict(m[:, sub], spy)

    f, ax, p = fig("e1_sharpe_histogram.png")
    ax.hist(sharpes, bins=60, color="#38bdf8", alpha=0.85)
    ax.axvline(sharpes[best_i], color="#f87171", lw=2, label=f"best IS Sharpe = {sharpes[best_i]:.2f}")
    ax.axvline(thr, color="#fbbf24", lw=2, ls="--", label=f"E[max Sharpe | luck, N={n_zoo}] = {thr:.2f}")
    ax.set_xlabel("in-sample Sharpe (annualized)")
    ax.set_ylabel("# strategies")
    ax.set_title("E1: 1,000 zero-skill strategies on real SPY")
    ax.legend()
    save(f, p)

    # --- repeated-zoo false-positive rate ------------------------------------
    fpr_rows = []
    for r in range(n_reps):
        mm = random_signal_matrix(spy, rep_size, seed=1000 + r)
        v, cscv, rcr, ss, bi = _zoo_verdict(mm, spy)
        fpr_rows.append({
            "rep": r, "dsr_p": v.components[0].score / 100,
            "pbo": cscv.pbo, "rc_p": rcr.p_value,
            "best_is_sharpe": float(ss[bi]),
            "score": v.score, "label": v.label,
        })
        print(f"rep {r}: label={v.label} score={v.score}")

    dsr_ps = np.array([x["dsr_p"] for x in fpr_rows])
    pbos = np.array([x["pbo"] for x in fpr_rows])
    labels = np.array([x["label"] for x in fpr_rows])
    scores = np.array([x["score"] for x in fpr_rows])
    # False positive = detector FAILS to flag a zero-skill zoo
    fpr_dsr = float(np.mean(dsr_ps > 0.5))
    fpr_pbo = float(np.mean(pbos < 0.25))
    fpr_either = float(np.mean((dsr_ps > 0.5) & (pbos < 0.25)))
    label_counts = {lab: int(np.sum(labels == lab)) for lab in ("Survives", "Unclear", "Mirage")}
    fpr_verdict = float(np.mean(labels == "Survives"))

    f, ax, p = fig("e1_detector_scores.png")
    ax.scatter(dsr_ps, pbos, c="#38bdf8", s=60, edgecolor="#0b1020")
    ax.axvline(0.05, color="#fbbf24", ls="--", label="DSR p = 0.05")
    ax.axhline(0.25, color="#f87171", ls="--", label="PBO = 0.25")
    ax.set_xlabel("DSR p-value (P(true skill))")
    ax.set_ylabel("PBO")
    ax.set_title(f"E1: {n_reps} zero-skill zoos x {rep_size} strategies")
    ax.legend()
    save(f, p)

    out = {
        "experiment": "E1 false positives",
        "headline": {
            "n_strategies": n_zoo,
            "best_is_sharpe": float(sharpes[best_i]),
            "psr": psr_p,
            "dsr_threshold": thr,
            "dsr_p": dsr_p,
            "pbo_200col": pbo,
            "reality_check_p": float(rc.p_value),
            "verdict_score": verdict.score,
            "verdict_label": verdict.label,
        },
        "false_positive_rates": {
            "n_reps": n_reps,
            "rep_size": rep_size,
            "fpr_dsr_at_0.5": fpr_dsr,
            "fpr_pbo_at_0.25": fpr_pbo,
            "fpr_dsr_and_pbo": fpr_either,
            "fpr_verdict_survives": fpr_verdict,
            "label_counts": label_counts,
            "mean_score": float(scores.mean()),
        },
        "reps": fpr_rows,
    }
    (REPORTS / "e1.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["false_positive_rates"], indent=1))
    return out


if __name__ == "__main__":
    run()
