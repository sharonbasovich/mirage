"""E2 - Detection power: synthetic strategies with planted, tunable skill.

For each annualized-Sharpe skill level s, N-1 iid noise strategies plus one
strategy with true daily drift giving Sharpe s.  A rep is POSITIVE when the
in-sample winner is the genuinely skilled strategy; the detectors must then
certify skill.  We report detection power vs skill and ROC/AUC for
DSR p-value and 1-PBO as classifiers of 'the IS winner has true skill'.
"""

from __future__ import annotations

import json

import numpy as np

from experiments.common import REPORTS, fig, roc_auc, save
from mirage.diagnostics.costs import cost_fragility
from mirage.diagnostics.cscv import cscv_pbo
from mirage.diagnostics.reality_check import reality_check
from mirage.diagnostics.sharpe import dsr, min_backtest_length, sharpe_ratio
from mirage.diagnostics.verdict import build_verdict

SKILL_LEVELS = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]


def run(n_strategies: int = 50, n_days: int = 2500, reps: int = 40,
        daily_vol: float = 0.01, seed: int = 11) -> dict:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for s in SKILL_LEVELS:
        mu = s * daily_vol / np.sqrt(252)
        for rep in range(reps):
            m = rng.normal(0.0, daily_vol, size=(n_days, n_strategies))
            if s > 0:
                m[:, 0] += mu  # strategy 0 carries the planted skill
            sharpes = np.array([sharpe_ratio(m[:, i]) for i in range(n_strategies)])
            bi = int(np.argmax(sharpes))
            d = dsr(m[:, bi], sharpes)
            cscv = cscv_pbo(m, n_blocks=8)
            pbo = cscv.pbo
            # full verdict: benchmark = a zero-skill buy-hold-like series
            bench = rng.normal(0.0002, daily_vol, size=n_days)
            rc = reality_check(m, bench, n_bootstrap=200, seed=rep)
            frag = cost_fragility(m[:, bi], (m[:, bi] != 0).astype(float))
            v = build_verdict(
                dsr_p=d, pbo=pbo,
                is_sharpe=float(np.median(cscv.is_sharpes)),
                oos_sharpe_median=float(np.median(cscv.oos_sharpes)),
                breakeven_bps=frag.breakeven_bps, assumed_cost_bps=5.0,
                n_days=n_days, min_btl=min_backtest_length(m[:, bi]),
                n_trials=n_strategies, rc_p=rc.p_value,
                breakeven_capped=frag.capped,
            )
            rows.append({
                "skill": s, "rep": rep, "winner_skilled": bool(s > 0 and bi == 0),
                "dsr_p": d, "pbo": pbo, "best_sharpe": float(sharpes.max()),
                "score": v.score, "label": v.label,
            })
        print(f"skill {s}: done")

    # Detection power among reps where the IS winner IS the skilled strategy:
    # detector should say "skill".  FPR among skill=0 reps.
    power = []
    for s in SKILL_LEVELS:
        sub = [r for r in rows if r["skill"] == s]
        winners = [r for r in sub if r["winner_skilled"]] or sub
        power.append({
            "skill": s,
            "winner_rate": float(np.mean([r["winner_skilled"] for r in sub])),
            "power_dsr": float(np.mean([r["dsr_p"] > 0.5 for r in winners])),
            "power_pbo": float(np.mean([r["pbo"] < 0.25 for r in winners])),
            "power_verdict": float(np.mean([r["label"] == "Survives" for r in winners])),
        })

    f, ax, p = fig("e2_power.png")
    ax.plot([x["skill"] for x in power], [x["power_dsr"] for x in power],
            "o-", color="#38bdf8", label="DSR p > 0.5")
    ax.plot([x["skill"] for x in power], [x["power_pbo"] for x in power],
            "s-", color="#fbbf24", label="PBO < 0.25")
    ax.plot([x["skill"] for x in power], [x["power_verdict"] for x in power],
            "^-", color="#34d399", label="verdict = Survives")
    ax.plot([x["skill"] for x in power], [x["winner_rate"] for x in power],
            ":", color="#6b7280", label="P(skilled strategy wins IS)")
    ax.set_xlabel("planted true Sharpe (annualized)")
    ax.set_ylabel("detection power")
    ax.set_title(f"E2: detector power vs planted skill ({reps} reps x {n_strategies} trials)")
    ax.legend()
    save(f, p)

    # ROC: positive = IS winner is the skilled strategy
    labels = np.array([1 if r["winner_skilled"] else 0 for r in rows])
    dsr_scores = np.array([r["dsr_p"] for r in rows])
    pbo_scores = np.array([1 - r["pbo"] for r in rows])
    f_d, t_d, auc_d = roc_auc(dsr_scores, labels)
    f_p, t_p, auc_p = roc_auc(pbo_scores, labels)

    # --- verdict label validated on ground truth ---------------------------
    truth = np.array([r["winner_skilled"] for r in rows])
    pred = np.array([r["label"] == "Survives" for r in rows])
    confusion = {
        "tp": int(np.sum(pred & truth)), "fp": int(np.sum(pred & ~truth)),
        "fn": int(np.sum(~pred & truth)), "tn": int(np.sum(~pred & ~truth)),
        "accuracy": float(np.mean(pred == truth)),
        "survives_rate_by_skill": {
            str(s): float(np.mean([r["label"] == "Survives"
                                   for r in rows if r["skill"] == s]))
            for s in SKILL_LEVELS},
    }
    print("label confusion:", json.dumps(confusion))

    f, ax, p = fig("e2_roc.png")
    ax.plot(f_d, t_d, color="#38bdf8", lw=2, label=f"DSR p-value (AUC {auc_d:.3f})")
    ax.plot(f_p, t_p, color="#fbbf24", lw=2, label=f"1 - PBO (AUC {auc_p:.3f})")
    ax.plot([0, 1], [0, 1], ":", color="#6b7280", label="chance")
    ax.set_xlabel("false positive rate")
    ax.set_ylabel("true positive rate")
    ax.set_title("E2: ROC - is the in-sample winner genuinely skilled?")
    ax.legend(loc="lower right")
    save(f, p)

    out = {
        "experiment": "E2 detection power",
        "n_strategies": n_strategies,
        "n_days": n_days,
        "reps": reps,
        "power": power,
        "auc": {"dsr": auc_d, "pbo": auc_p},
        "label_confusion": confusion,
        "roc": {"dsr": {"fpr": f_d.tolist(), "tpr": t_d.tolist()},
                "pbo": {"fpr": f_p.tolist(), "tpr": t_p.tolist()}},
        "raw": rows,
    }
    (REPORTS / "e2.json").write_text(json.dumps(out, indent=2))
    print("AUC:", out["auc"])
    return out


if __name__ == "__main__":
    run()
