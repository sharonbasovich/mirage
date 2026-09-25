"""Multiple-testing haircuts (Harvey & Liu 2015, 'Backtesting').

Given the per-trial p-values for "true Sharpe <= 0", compute adjusted
significance of the best trial under:
  - Bonferroni (family-wise)
  - Holm (family-wise, step-down)
  - BHY (Benjamini-Hochberg-Yekutieli, FDR under dependence)
"""

from __future__ import annotations

import numpy as np


def haircut_adjusted_pvalues(p_values: np.ndarray) -> dict[str, float]:
    """Adjusted p-value for the smallest observed p-value under each method."""
    p = np.asarray(p_values, dtype=float)
    p = p[np.isfinite(p)]
    n = len(p)
    if n == 0:
        return {"bonferroni": 1.0, "holm": 1.0, "bhy": 1.0}
    p_sorted = np.sort(p)

    bonf = min(1.0, n * p_sorted[0])

    # Holm step-down adjusted p-values: adj_i = max_{j<=i} min((n - j + 1) p_j, 1)
    holm_adj = np.maximum.accumulate(np.minimum((n - np.arange(n)) * p_sorted, 1.0))
    holm = float(min(1.0, holm_adj[0]))

    # BHY adjusted p-values: q_i = p_(i) * n * c(n) / i, enforced monotone
    cn = float(np.sum(1.0 / np.arange(1, n + 1)))
    ranks = np.arange(1, n + 1)
    q = p_sorted * n * cn / ranks
    bhy_adj = np.minimum.accumulate(q[::-1])[::-1]
    bhy = float(min(1.0, bhy_adj[0]))

    return {"bonferroni": bonf, "holm": holm, "bhy": bhy}
