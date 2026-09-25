"""Stationary-bootstrap Reality Check.

References
----------
White, H. (2000) "A Reality Check for Data Snooping", Econometrica 68(5).
Politis, D. & Romano, J. (1994) "The Stationary Bootstrap", JASA 89(428).

Tests whether the best of N strategies beats the benchmark beyond luck.
For each strategy k let d_k = r_k - r_bench. The test statistic is
V = max_k mean(d_k). Under the stationary bootstrap we recenter each
resample and compare the bootstrapped max to V.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class RealityCheckResult:
    p_value: float
    stat: float  # observed max mean excess return vs benchmark
    best_index: int
    n_bootstrap: int
    avg_block: float
    boot_stats: np.ndarray


def stationary_bootstrap_indices(
    n: int,
    avg_block: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """One stationary-bootstrap resample of indices 0..n-1 (Politis & Romano)."""
    p = 1.0 / max(1.0, avg_block)
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(0, n)
    for i in range(1, n):
        if rng.random() < p:
            idx[i] = rng.integers(0, n)
        else:
            idx[i] = (idx[i - 1] + 1) % n
    return idx


def reality_check(
    strategy_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    n_bootstrap: int = 500,
    avg_block: float = 10.0,
    seed: int = 0,
) -> RealityCheckResult:
    """White's Reality Check.

    Parameters
    ----------
    strategy_returns : (T, N) daily returns of N strategies
    benchmark_returns : (T,) daily returns of the benchmark
    """
    rng = np.random.default_rng(seed)
    m = np.asarray(strategy_returns, dtype=float)
    bench = np.asarray(benchmark_returns, dtype=float)
    t, n = m.shape
    m = np.nan_to_num(m)
    bench = np.nan_to_num(bench)
    if len(bench) != t:
        raise ValueError("benchmark length must match strategies")

    d = m - bench[:, None]  # (T, N) excess returns
    obs_mean = d.mean(axis=0)
    stat = float(obs_mean.max())
    best = int(obs_mean.argmax())

    boot_stats = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        idx = stationary_bootstrap_indices(t, avg_block, rng)
        dm = d[idx].mean(axis=0)
        # recentered bootstrap max (White 2000)
        boot_stats[b] = float((dm - obs_mean).max())

    p_value = float(np.mean(boot_stats >= stat))
    return RealityCheckResult(
        p_value=p_value,
        stat=stat,
        best_index=best,
        n_bootstrap=n_bootstrap,
        avg_block=avg_block,
        boot_stats=boot_stats,
    )
