"""Shared helpers for experiments."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPORTS = Path(__file__).resolve().parent.parent / "reports"
FIGS = REPORTS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

DARK = {
    "figure.facecolor": "#0b1020",
    "axes.facecolor": "#111827",
    "axes.edgecolor": "#374151",
    "axes.labelcolor": "#e5e7eb",
    "text.color": "#e5e7eb",
    "xtick.color": "#9ca3af",
    "ytick.color": "#9ca3af",
    "grid.color": "#1f2937",
    "axes.grid": True,
    "font.size": 11,
}


def fig(name: str):
    plt.rcParams.update(DARK)
    f, ax = plt.subplots(figsize=(8, 4.6), dpi=140)
    return f, ax, FIGS / name


def save(f, path):
    f.tight_layout()
    f.savefig(path, facecolor=f.get_facecolor())
    plt.close(f)
    print("wrote", path)


def random_signal_matrix(asset_returns: np.ndarray, n_strategies: int, seed: int) -> np.ndarray:
    """Zero-skill strategies: iid {-1,0,+1} positions applied to real returns."""
    rng = np.random.default_rng(seed)
    pos = rng.choice([-1.0, 0.0, 1.0], size=(len(asset_returns), n_strategies))
    return pos * asset_returns[:, None]


def roc_auc(scores: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """ROC curve + AUC for a score where higher = 'skill present'."""
    order = np.argsort(-scores)
    labels = np.asarray(labels)[order]
    P = labels.sum()
    N = len(labels) - P
    tpr = np.concatenate([[0.0], np.cumsum(labels) / max(P, 1)])
    fpr = np.concatenate([[0.0], np.cumsum(1 - labels) / max(N, 1)])
    auc = float(np.trapezoid(tpr, fpr))
    return fpr, tpr, auc
