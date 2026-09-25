"""Purged k-fold cross-validation with embargo + walk-forward splits.

Reference
---------
Lopez de Prado, M. (2018) "Advances in Financial Machine Learning", ch. 7.

Each sample i carries a label interval [t0_i, t1_i] (e.g., a next-day-return
label has t1 = t0 + 1). For a test fold spanning [a, b]:

  - purge: drop train samples whose label interval intersects [a, b]
  - embargo: drop train samples with t0 in (b, b + embargo]
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PurgedKFold:
    n_splits: int = 5
    embargo: int = 1  # days after each test fold during which train labels are dropped

    def split(
        self,
        t0: np.ndarray,
        t1: np.ndarray,
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        t0 = np.asarray(t0)
        t1 = np.asarray(t1)
        n = len(t0)
        edges = np.linspace(0, n, self.n_splits + 1).astype(int)
        out: list[tuple[np.ndarray, np.ndarray]] = []
        for k in range(self.n_splits):
            a, b = int(edges[k]), int(edges[k + 1]) - 1
            test_idx = np.arange(a, b + 1)
            # interval overlap with [a, b]
            overlap = (t0 <= b) & (t1 >= a)
            # embargo window after the test fold
            embargoed = (t0 > b) & (t0 <= b + self.embargo)
            train_idx = np.where(~(overlap | embargoed))[0]
            out.append((train_idx, test_idx))
        return out


def walk_forward_splits(
    n: int,
    train_window: int,
    test_window: int,
    embargo: int = 1,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Anchored walk-forward: expanding train window, fixed test horizon."""
    out: list[tuple[np.ndarray, np.ndarray]] = []
    start = train_window
    while start < n:
        train_idx = np.arange(0, start - embargo)
        test_idx = np.arange(start, min(start + test_window, n))
        if len(test_idx) == 0 or len(train_idx) == 0:
            break
        out.append((train_idx, test_idx))
        start += test_window
    return out
