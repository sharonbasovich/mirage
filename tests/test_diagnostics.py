"""Analytic/sanity tests for the diagnostics battery."""

import numpy as np
import pytest

from mirage.diagnostics.costs import cost_fragility
from mirage.diagnostics.cscv import cscv_pbo
from mirage.diagnostics.cv import PurgedKFold, walk_forward_splits
from mirage.diagnostics.haircuts import haircut_adjusted_pvalues
from mirage.diagnostics.reality_check import reality_check, stationary_bootstrap_indices
from mirage.diagnostics.sharpe import (
    dsr,
    dsr_expected_max_sharpe,
    min_backtest_length,
    psr,
    sharpe_ratio,
)
from mirage.diagnostics.verdict import build_verdict

RNG = np.random.default_rng(42)


def iid(n, mu=0.0, sd=0.01, seed=0):
    return np.random.default_rng(seed).normal(mu, sd, n)


# --- Sharpe / PSR / DSR ---------------------------------------------------


def test_sharpe_zero_on_constant_returns():
    assert sharpe_ratio(np.zeros(100)) == 0.0


def test_sharpe_sign():
    r = iid(500, mu=0.001, sd=0.01)
    assert sharpe_ratio(r) > 0
    assert sharpe_ratio(-r) < 0


def test_psr_bounds_and_monotonicity():
    r_neg = iid(500, mu=-0.002, sd=0.01)
    r_pos = iid(500, mu=0.002, sd=0.01)
    p_neg, p_pos = psr(r_neg), psr(r_pos)
    assert 0 <= p_neg <= 1 and 0 <= p_pos <= 1
    assert p_pos > 0.9 > p_neg


def test_psr_benchmark():
    r = iid(2000, mu=0.0005, sd=0.01)
    # higher benchmark -> lower PSR
    assert psr(r, 0.0) > psr(r, 1.0)


def test_dsr_expected_max_grows_with_trials():
    sr = np.array([0.5, 0.3, -0.2, 0.1] * 10)
    e10 = dsr_expected_max_sharpe(sr, n_trials=10)
    e100 = dsr_expected_max_sharpe(sr, n_trials=100)
    assert e100 > e10 > 0


def test_dsr_single_trial_uses_zero_threshold():
    r = iid(500, mu=0.001, sd=0.01)
    assert dsr(r, np.array([0.5])) == pytest.approx(psr(r, 0.0))


def test_min_btl_infinite_for_negative_edge():
    r = iid(500, mu=-0.001, sd=0.01)
    assert min_backtest_length(r) == float("inf")


def test_min_btl_reasonable_for_strong_edge():
    r = iid(5000, mu=0.002, sd=0.01)
    m = min_backtest_length(r)
    assert np.isfinite(m) and m < 5000


# --- CSCV / PBO -----------------------------------------------------------


def test_pbo_near_half_on_pure_noise():
    # iid noise trials: IS winner is a coin flip OOS -> PBO ~ 0.5
    m = RNG.normal(0, 0.01, size=(512, 24))
    res = cscv_pbo(m, n_blocks=16)
    assert 0.35 <= res.pbo <= 0.65
    assert res.n_combinations == 12870


def test_pbo_low_with_planted_skill():
    # one strategy has large persistent edge -> it wins IS *and* OOS -> low PBO
    m = RNG.normal(0, 0.01, size=(512, 24))
    m[:, 3] += 0.004  # huge edge: daily mu 40bps on 1% vol
    res = cscv_pbo(m, n_blocks=16)
    assert res.pbo < 0.10


def test_pbo_high_when_skill_is_localized():
    # edge lives in only 2 of 16 blocks: combos selecting it IS lose OOS
    m = RNG.normal(0, 0.01, size=(512, 24))
    m[:64, 0] += 0.006
    res = cscv_pbo(m, n_blocks=16)
    assert res.pbo > 0.4


def test_cscv_shapes():
    m = RNG.normal(0, 0.01, size=(256, 8))
    res = cscv_pbo(m, n_blocks=8)
    assert res.lambdas.shape == res.is_sharpes.shape == res.oos_sharpes.shape
    assert 0 <= res.p_oos_loss <= 1


# --- Purged CV / walk-forward ----------------------------------------------


def test_purged_kfold_no_overlap():
    n = 100
    t0 = np.arange(n)
    t1 = t0 + 1  # next-day labels
    pkf = PurgedKFold(n_splits=5, embargo=3)
    for train, test in pkf.split(t0, t1):
        a, b = int(test[0]), int(test[-1])
        # purge: no train sample's label interval [t0, t1] may overlap [a, b]
        for i in train:
            assert not (t0[i] <= b and t1[i] >= a), f"leaky train sample {i} vs test [{a},{b}]"
        # embargo: no train sample starting in (b, b+3]
        assert not np.any((t0[train] > b) & (t0[train] <= b + 3))


def test_walk_forward_expands():
    splits = walk_forward_splits(300, train_window=100, test_window=50, embargo=1)
    assert len(splits) == 4
    tr0, te0 = splits[0]
    assert tr0[-1] < te0[0]
    assert splits[1][0][-1] >= splits[0][0][-1]


# --- Reality Check ---------------------------------------------------------


def test_rc_high_p_on_noise():
    m = RNG.normal(0, 0.01, size=(400, 20))
    bench = RNG.normal(0, 0.01, size=400)
    res = reality_check(m, bench, n_bootstrap=200, seed=1)
    assert res.p_value > 0.1


def test_rc_low_p_with_real_edge():
    m = RNG.normal(0, 0.01, size=(400, 20))
    m[:, 5] += 0.003
    bench = RNG.normal(0, 0.01, size=400)
    res = reality_check(m, bench, n_bootstrap=200, seed=1)
    assert res.p_value < 0.1
    assert res.best_index == 5


def test_stationary_bootstrap_valid_indices():
    idx = stationary_bootstrap_indices(100, 10.0, np.random.default_rng(0))
    assert len(idx) == 100 and idx.min() >= 0 and idx.max() < 100


# --- Cost fragility --------------------------------------------------------


def test_cost_fragility_zero_turnover():
    g = iid(300, mu=0.001, sd=0.01)
    u = np.zeros(300)
    res = cost_fragility(g, u)
    assert res.breakeven_bps == 300.0  # never crosses
    assert np.allclose(res.sharpe_curve, res.sharpe_curve[0])


def test_cost_fragility_crosses():
    g = np.full(300, 0.0002)  # tiny positive drift, zero vol won't happen; add noise
    g = g + iid(300, 0, 0.005)
    u = np.ones(300)  # full turnover daily: very fragile
    res = cost_fragility(g, u, assumed_cost_bps=5.0)
    assert res.breakeven_bps < 50


# --- Haircuts ---------------------------------------------------------------


def test_haircuts_bonferroni():
    p = np.array([0.001, 0.4, 0.6])
    adj = haircut_adjusted_pvalues(p)
    assert adj["bonferroni"] == pytest.approx(0.003)
    assert adj["holm"] == pytest.approx(0.003)
    assert adj["bhy"] >= adj["bonferroni"] * 0  # sanity only


def test_haircuts_many_nulls():
    p = np.concatenate([[0.0001], RNG.uniform(0.2, 0.9, 49)])
    adj = haircut_adjusted_pvalues(p)
    assert adj["bonferroni"] < 0.01
    assert adj["bhy"] > adj["bonferroni"]  # BHY more lenient than Bonferroni


# --- Verdict ----------------------------------------------------------------


def test_verdict_labels():
    v_bad = build_verdict(dsr_p=0.01, pbo=0.9, is_sharpe=2.0, oos_sharpe_median=-0.2,
                          breakeven_bps=2, assumed_cost_bps=5, n_days=500,
                          min_btl=5000, n_trials=200)
    assert v_bad.label == "Mirage" and v_bad.score < 40
    v_good = build_verdict(dsr_p=0.99, pbo=0.1, is_sharpe=1.0, oos_sharpe_median=1.0,
                           breakeven_bps=300, assumed_cost_bps=5, n_days=5000,
                           min_btl=100, n_trials=10)
    assert v_good.label == "Survives" and v_good.score > 65
    assert len(v_bad.components) == 5
    assert sum(c.weight for c in v_bad.components) == pytest.approx(1.0)
