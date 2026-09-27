"""Sharpe-ratio statistics: PSR, DSR, Minimum Backtest Length.

References
----------
Bailey, D. & Lopez de Prado, M. (2012) "The Sharpe Ratio Efficient Frontier",
Journal of Risk 15(2).  (PSR, MinTRL)
Bailey, D. & Lopez de Prado, M. (2014) "The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting and Non-Normality",
Journal of Portfolio Management 40(5).  (DSR)
"""

from __future__ import annotations

import numpy as np
from scipy import stats

TRADING_DAYS = 252
EULER_MASCHERONI = 0.5772156649015329


def sharpe_ratio(returns: np.ndarray, periods_per_year: int = TRADING_DAYS) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2:
        return 0.0
    sd = r.std(ddof=1)
    if sd <= 0:
        return 0.0
    return float(r.mean() / sd * np.sqrt(periods_per_year))


def _moments(returns: np.ndarray) -> tuple[float, float, int]:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 3:
        return 0.0, 3.0, len(r)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))
    return skew, kurt, len(r)


def psr(
    returns: np.ndarray,
    sr_benchmark: float = 0.0,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Probabilistic Sharpe Ratio: confidence that true SR > sr_benchmark.

    Returns a probability in [0, 1]. ``returns`` are per-period returns and
    ``sr_benchmark`` is an annualized Sharpe threshold.  The test statistic is
    in per-period units (Bailey & Lopez de Prado 2012), so both Sharpes are
    de-annualized before entering it.
    """
    sr = sharpe_ratio(returns, periods_per_year)
    skew, kurt, t = _moments(returns)
    if t < 2:
        return 0.0
    ann = np.sqrt(periods_per_year)
    sr_p = sr / ann
    sr_b = sr_benchmark / ann
    denom = np.sqrt(max(1e-12, 1 - skew * sr_p + (kurt - 1) / 4 * sr_p**2))
    z = (sr_p - sr_b) * np.sqrt(t - 1) / denom
    return float(stats.norm.cdf(z))


def dsr_expected_max_sharpe(trial_sharpes: np.ndarray, n_trials: int | None = None) -> float:
    """E[max Sharpe] over N trials under the null (independent trials).

    Bailey & Lopez de Prado (2014), eq. for E[max_N]:
        E[max_N] ~ (1-g) Z^{-1}(1 - 1/N) + g Z^{-1}(1 - 1/(N e))
    scaled by sqrt(Var_N) of the trial Sharpe estimates.
    """
    sr = np.asarray(trial_sharpes, dtype=float)
    sr = sr[np.isfinite(sr)]
    n = int(n_trials or len(sr))
    if n <= 1 or len(sr) < 2:
        return 0.0
    var_n = float(np.var(sr, ddof=1))
    z1 = stats.norm.ppf(1 - 1.0 / n)
    z2 = stats.norm.ppf(1 - 1.0 / (n * np.e))
    e_max = (1 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2
    return float(np.sqrt(var_n) * e_max)


def dsr(
    best_returns: np.ndarray,
    trial_sharpes: np.ndarray,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Deflated Sharpe Ratio: PSR of the *selected* trial vs E[max SR] under H0.

    Returns a probability in [0, 1]; low values mean the best in-sample
    result is consistent with luck across all trials.
    """
    threshold = dsr_expected_max_sharpe(trial_sharpes)
    return psr(best_returns, sr_benchmark=threshold, periods_per_year=periods_per_year)


def min_backtest_length(
    returns: np.ndarray,
    sr_benchmark: float = 0.0,
    confidence: float = 0.95,
    periods_per_year: int = TRADING_DAYS,
) -> float:
    """Minimum number of observations needed for SR > sr_benchmark at ``confidence``.

    Bailey & Lopez de Prado (2012), MinTRL:
        MinTRL = 1 + (1 - g3 SR + (g4 - 1)/4 SR^2) (z_a / (SR - SR*))^2
    """
    sr = sharpe_ratio(returns, periods_per_year)
    skew, kurt, _ = _moments(returns)
    z = float(stats.norm.ppf(confidence))
    ann = np.sqrt(periods_per_year)
    sr_p = sr / ann
    diff = (sr - sr_benchmark) / ann
    if diff <= 0:
        return float("inf")
    factor = 1 - skew * sr_p + (kurt - 1) / 4 * sr_p**2
    return float(1 + max(0.0, factor) * (z / diff) ** 2)
