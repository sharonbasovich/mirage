"""Probability of Backtest Overfitting via Combinatorially Symmetric CV.

Reference
---------
Bailey, D., Borwein, J., Lopez de Prado, M. & Zhu, Q. (2017)
"The Probability of Backtest Overfitting", Journal of Computational Finance.

Given a T x N matrix of daily returns for N candidate configurations of a
strategy, partition the sample into S contiguous blocks. For each of the
C(S, S/2) ways to pick half the blocks as the in-sample (IS) set:

  - rank configurations by IS Sharpe, take the IS winner n*
  - take n*'s rank on the out-of-sample (OOS) complement, normalized to
    omega in (0, 1); lambda = logit(omega)

PBO = fraction of combinations with lambda < 0 (the IS winner ranks below
median out of sample).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np


@dataclass
class CSCVResult:
    pbo: float
    lambdas: np.ndarray  # logit of normalized OOS rank, per combination
    is_sharpes: np.ndarray  # IS Sharpe of the chosen config, per combination
    oos_sharpes: np.ndarray  # OOS Sharpe of the chosen config, per combination
    p_oos_loss: float  # P(OOS Sharpe of IS winner < 0)
    degradation_slope: float  # slope of OOS-vs-IS Sharpe regression
    n_combinations: int
    n_trials: int
    n_blocks: int
    dominance: dict = field(default_factory=dict)  # stochastic-dominance plot data


def _block_stats(returns: np.ndarray, n_blocks: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Split T days into n_blocks contiguous blocks; per-block sums/sumsq/count."""
    t, n = returns.shape
    edges = np.linspace(0, t, n_blocks + 1).astype(int)
    sums = np.zeros((n_blocks, n))
    ssq = np.zeros((n_blocks, n))
    cnt = np.zeros(n_blocks)
    for i in range(n_blocks):
        block = returns[edges[i] : edges[i + 1]]
        sums[i] = block.sum(axis=0)
        ssq[i] = (block**2).sum(axis=0)
        cnt[i] = block.shape[0]
    return sums, ssq, cnt


def _sub_sharpe(sums: np.ndarray, ssq: np.ndarray, cnt: np.ndarray, blocks: np.ndarray) -> np.ndarray:
    """Sharpe of each strategy over the union of ``blocks`` (unannualized)."""
    s = sums[blocks].sum(axis=0)
    q = ssq[blocks].sum(axis=0)
    c = cnt[blocks].sum()
    mean = s / c
    var = np.maximum(q / c - mean**2, 1e-18)
    return mean / np.sqrt(var)


def cscv_pbo(returns: np.ndarray, n_blocks: int = 16,
             periods_per_year: int = 252) -> CSCVResult:
    """Compute PBO and companion statistics.

    Parameters
    ----------
    returns : ndarray, shape (T, N)
        Daily returns of N candidate configurations (aligned, no NaNs).
    n_blocks : int
        Number of contiguous blocks S (must be even; paper uses 16).
    periods_per_year : int
        Annualization factor for the reported is_sharpes / oos_sharpes
        (ranks and lambdas are scale-invariant; only reporting changes).
    """
    m = np.asarray(returns, dtype=float)
    if m.ndim != 2:
        raise ValueError("returns must be a T x N matrix")
    t, n = m.shape
    if n < 2:
        raise ValueError("need at least 2 configurations")
    if n_blocks % 2:
        raise ValueError("n_blocks must be even")
    if t < n_blocks * 4:
        raise ValueError("sample too short for the requested block count")
    m = np.nan_to_num(m, nan=0.0, posinf=0.0, neginf=0.0)

    sums, ssq, cnt = _block_stats(m, n_blocks)
    half = n_blocks // 2
    all_blocks = np.arange(n_blocks)

    lambdas: list[float] = []
    is_sr: list[float] = []
    oos_sr: list[float] = []

    for combo in itertools.combinations(range(n_blocks), half):
        is_blocks = np.asarray(combo)
        oos_blocks = np.setdiff1d(all_blocks, is_blocks)
        is_perf = _sub_sharpe(sums, ssq, cnt, is_blocks)
        oos_perf = _sub_sharpe(sums, ssq, cnt, oos_blocks)
        n_star = int(np.argmax(is_perf))
        # normalized OOS rank of the IS winner, ascending (worst=1/(N+1))
        rank = 1 + int(np.sum(oos_perf < oos_perf[n_star]))
        omega = rank / (n + 1)
        lam = np.log(omega / (1 - omega))
        lambdas.append(float(lam))
        is_sr.append(float(is_perf[n_star]))
        oos_sr.append(float(oos_perf[n_star]))

    lambdas_arr = np.asarray(lambdas)
    ann = np.sqrt(periods_per_year)
    is_arr = np.asarray(is_sr) * ann
    oos_arr = np.asarray(oos_sr) * ann

    pbo = float(np.mean(lambdas_arr < 0))
    p_loss = float(np.mean(oos_arr < 0))

    if np.std(is_arr) > 0:
        slope = float(np.polyfit(is_arr, oos_arr, 1)[0])
    else:
        slope = 0.0

    sorted_l = np.sort(lambdas_arr)
    dominance = {
        "lambda": sorted_l.tolist(),
        "cdf": (np.arange(1, len(sorted_l) + 1) / len(sorted_l)).tolist(),
    }

    return CSCVResult(
        pbo=pbo,
        lambdas=lambdas_arr,
        is_sharpes=is_arr,
        oos_sharpes=oos_arr,
        p_oos_loss=p_loss,
        degradation_slope=slope,
        n_combinations=len(lambdas),
        n_trials=n,
        n_blocks=n_blocks,
        dominance=dominance,
    )
