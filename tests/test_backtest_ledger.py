"""Backtester no-lookahead, ledger hash chain, program integration."""

import numpy as np
import pandas as pd

from mirage.backtest import perf_stats, run_backtest
from mirage.ledger import Ledger, new_program_id


def make_prices(n=100, seed=0):
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0005, 0.01, n)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    close = pd.Series(100 * np.exp(np.cumsum(r)), index=dates, name="SPY")
    return close.to_frame()


def test_no_lookahead_shift():
    """Positions are decided at close t and applied from t+1.

    A 'signal' equal to today's return sign would earn |r| every day if the
    backtester leaked; with the shift it earns sign(r_{t-1}) * r_t instead.
    """
    prices = make_prices(50)
    rets = prices.pct_change().fillna(0.0)
    sig = np.sign(rets)  # uses today's close -> only valid from tomorrow
    sig.columns = prices.columns
    bt = run_backtest(prices, sig, cost_bps=0)
    expected = (np.sign(rets.shift(1).fillna(0.0)) * rets).sum(axis=1)
    np.testing.assert_allclose(bt.gross_returns.to_numpy(), expected.to_numpy(), atol=1e-10)
    leaked = rets.abs().sum(axis=1)  # what a leaky backtester would report
    assert abs(bt.gross_returns.mean()) < leaked.mean()


def test_zero_position_zero_return():
    prices = make_prices(50)
    pos = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    bt = run_backtest(prices, pos, cost_bps=10)
    assert bt.returns.abs().max() == 0.0


def test_buy_hold_matches_asset():
    prices = make_prices(50)
    pos = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    bt = run_backtest(prices, pos, cost_bps=0)
    asset = prices.pct_change().fillna(0).iloc[:, 0]
    # first day earns 0 (position applied from day 1)
    np.testing.assert_allclose(bt.gross_returns.iloc[1:].to_numpy(), asset.iloc[1:].to_numpy())


def test_costs_reduce_returns():
    prices = make_prices(50)
    pos = pd.DataFrame(np.sign(np.sin(np.arange(50) / 3)), index=prices.index,
                       columns=prices.columns)
    free = run_backtest(prices, pos, cost_bps=0)
    costly = run_backtest(prices, pos, cost_bps=50)
    assert (costly.returns <= free.returns + 1e-12).all()
    assert costly.returns.sum() < free.returns.sum()


def test_perf_stats_keys():
    prices = make_prices(100)
    pos = pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
    bt = run_backtest(prices, pos)
    st = perf_stats(bt.returns)
    assert {"sharpe", "ann_return", "ann_vol", "max_drawdown", "days"} <= set(st)


# --- Ledger ------------------------------------------------------------------


def test_ledger_chain_and_tamper(tmp_path):
    led = Ledger(tmp_path / "l.db")
    pid = new_program_id("test")
    led.append(pid, "t1", {"a": 1}, "dh", {"sharpe": 1.0}, "rh1")
    led.append(pid, "t2", {"a": 2}, "dh", {"sharpe": 0.5}, "rh2")
    ok, msg = led.verify_chain()
    assert ok, msg
    assert led.trial_count(pid) == 2

    # tamper: rewrite a metrics_json directly
    import sqlite3

    con = sqlite3.connect(tmp_path / "l.db")
    con.execute("UPDATE entries SET metrics_json='{\"sharpe\": 9.9}' WHERE id=1")
    con.commit()
    con.close()
    ok, msg = led.verify_chain()
    assert not ok


def test_ledger_certificate(tmp_path):
    led = Ledger(tmp_path / "l.db")
    pid = new_program_id("cert")
    led.append(pid, "t1", {"a": 1}, "dh", {"sharpe": 1.0}, "rh1")
    cert = led.export_certificate(pid, verdict={"label": "Mirage"})
    assert cert["trial_count"] == 1
    assert cert["chain_valid"]
    assert cert["best_trial"]["label"] == "t1"
    assert cert["verdict"]["label"] == "Mirage"
