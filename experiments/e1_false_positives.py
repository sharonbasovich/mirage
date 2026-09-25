"""E1 - False-positive rate.

1,000 zero-skill strategies on real SPY returns: the best in-sample Sharpe
looks great but the diagnostics must flag it.  We then measure the detector's
false-positive rate at standard thresholds over repeated independent zoos.
"""

from __future__ import annotations

import json

import numpy as np

from experiments.common import FIGS, REPORTS, fig, random_signal_matrix, save
from mirage.data import load_close
from mirage.diagnostics.cscv import cscv_pbo
from mirage.diagnostics.sharpe import dsr, dsr_expected_max_sharpe, psr, sharpe_ratio


def run(n_zoo: int = 1000, n_reps: int = 20, rep_size: int = 100, seed: int = 7) -> dict:
    spy = load_close("SPY").pct_change().dropna().to_numpy()

    # --- headline: one big random zoo on real data ---------------------------
    m = random_signal_matrix(spy, n_zoo, seed=seed)
    sharpes = np.array([sharpe_ratio(m[:, i]) for i in range(m.shape[1])])
    best_i = int(np.argmax(sharpes))
    thr = dsr_expected_max_sharpe(sharpes)
    dsr_p = dsr(m[:, best_i], sharpes)
    psr_p = psr(m[:, best_i])
    # PBO on a random subset of 200 columns (all-1000 is computable but slow to
    # plot; the statistic barely changes)
    sub = np.random.default_rng(seed).choice(m.shape[1], 200, replace=False)
    pbo = cscv_pbo(m[:, sub], n_blocks=16).pbo

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
        ss = np.array([sharpe_ratio(mm[:, i]) for i in range(rep_size)])
        bi = int(np.argmax(ss))
        d = dsr(mm[:, bi], ss)
        p = cscv_pbo(mm, n_blocks=8).pbo
        fpr_rows.append({"rep": r, "dsr_p": d, "pbo": p, "best_is_sharpe": float(ss[bi])})

    dsr_ps = np.array([x["dsr_p"] for x in fpr_rows])
    pbos = np.array([x["pbo"] for x in fpr_rows])
    # False positive = detector FAILS to flag overfitting
    fpr_dsr = float(np.mean(dsr_ps > 0.05))
    fpr_pbo = float(np.mean(pbos < 0.25))
    fpr_either = float(np.mean((dsr_ps > 0.05) & (pbos < 0.25)))

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
        },
        "false_positive_rates": {
            "n_reps": n_reps,
            "rep_size": rep_size,
            "fpr_dsr_at_0.05": fpr_dsr,
            "fpr_pbo_at_0.25": fpr_pbo,
            "fpr_both": fpr_either,
        },
        "reps": fpr_rows,
    }
    (REPORTS / "e1.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["headline"], indent=2))
    print(json.dumps(out["false_positive_rates"], indent=2))
    return out


if __name__ == "__main__":
    run()
