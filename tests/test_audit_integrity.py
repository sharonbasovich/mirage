"""Audit-integrity tests: the declared trial count is applied *before* the
verdict is built, and dishonest/unestimable inputs are rejected rather than
silently absorbed."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from mirage import api, cli
from mirage.diagnostics.sharpe import dsr_expected_max_sharpe, psr, sharpe_ratio
from mirage.program import analyze_returns_matrix


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("MIRAGE_YAHOO_DIR", str(tmp_path / "no-yahoo"))
    return TestClient(api.app)


def _returns_frame(rows: int = 500, cols: int = 5, seed: int = 0,
                   mu: float = 0.0008, dates: bool = True) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({f"s{i}": rng.normal(mu, 0.01, rows) for i in range(cols)})
    if dates:
        df.insert(0, "Date", pd.bdate_range("2020-01-01", periods=rows))
    return df


def _post(client, df: pd.DataFrame, n_trials: int, **form):
    csv = df.to_csv(index=False).encode()
    return client.post("/api/audit", files={"file": ("r.csv", csv, "text/csv")},
                       data={"n_trials": str(n_trials), **form})


# --- the confirmed P1: declared count must drive every dependent output ----


def test_declared_trials_drives_dsr_verdict_and_narrative(client):
    df = _returns_frame()
    r = _post(client, df, 10000)
    assert r.status_code == 200, r.text
    a = r.json()["analysis"]
    assert a["n_trials"] == 10000
    assert a["observed_trials"] == 5
    assert a["declared_trials"] == 10000

    # dsr is exactly PSR of the best column vs the best-of-10000 threshold
    ppy = a["periods_per_year"]
    sharpes = np.array([sharpe_ratio(df[c].to_numpy(), ppy) for c in
                        df.select_dtypes("number").columns])
    thr = dsr_expected_max_sharpe(sharpes, n_trials=10000)
    best = df[a["best_label"]].to_numpy()
    assert a["dsr_threshold"] == pytest.approx(thr)
    assert a["dsr"] == pytest.approx(psr(best, sr_benchmark=thr,
                                       periods_per_year=ppy))

    # the verdict consumed the declared count: component, score, narrative
    dsr_comp = next(c for c in a["verdict"]["components"] if c["key"] == "dsr")
    assert "10000" in dsr_comp["detail"]
    assert dsr_comp["score"] == pytest.approx(round(100 * a["dsr"], 1), abs=0.2)
    w = sum(c["weight"] for c in a["verdict"]["components"])
    expected = sum(c["weight"] * c["score"]
                   for c in a["verdict"]["components"]) / w
    assert a["verdict"]["score"] == pytest.approx(expected, abs=0.1)
    assert any("not seen" in n for n in a["verdict"]["narrative"])


def test_declared_count_changes_score_and_label(client):
    """Counterexample: the same upload survives at declared=5 but not 10000."""
    df = _returns_frame(seed=2)
    a5 = _post(client, df, 5).json()["analysis"]
    a10k = _post(client, df, 10000).json()["analysis"]
    assert a5["verdict"]["label"] == "Survives" and a5["verdict"]["score"] >= 65
    assert a10k["dsr"] < 0.01
    assert a10k["verdict"]["score"] < 65
    assert a10k["verdict"]["label"] == "Unclear"


def test_incomplete_upload_caps_label_at_unclear(client):
    """declared > observed: even when the heuristic score clears the
    Survives bar, a subset upload can never certify the unseen trials."""
    df = _returns_frame()  # seed 0: raw score clears the bar when extrapolated
    a = _post(client, df, 1000).json()["analysis"]
    assert a["verdict"]["score"] >= 65          # heuristic score still shown
    assert a["verdict"]["label"] == "Unclear"  # label is capped anyway
    assert a["verdict"]["label_capped"] is True
    assert any("capped at Unclear" in n for n in a["verdict"]["narrative"])

    # declared == observed is a full-matrix audit: no cap
    a_full = _post(client, df, 5).json()["analysis"]
    assert a_full["verdict"]["label"] == "Survives"
    assert a_full["verdict"]["label_capped"] is False


def test_cli_audit_matches_api_path(tmp_path, client):
    df = _returns_frame(seed=2)
    p = tmp_path / "r.csv"
    df.to_csv(p, index=False)
    res = CliRunner().invoke(cli.app, ["audit", str(p), "--trials", "10000"])
    assert res.exit_code == 0, res.output
    out = json.loads(res.stdout)
    api_out = _post(client, df, 10000).json()["analysis"]
    assert out["dsr"] == pytest.approx(api_out["dsr"])
    assert out["n_trials"] == 10000 and out["observed_trials"] == 5
    assert out["score"] == api_out["verdict"]["score"]
    assert out["verdict"] == api_out["verdict"]["label"]


# --- contradictory / unestimable inputs are rejected, not absorbed ----------


def _dated_rows(df: pd.DataFrame, dates, fmt: str = "%Y-%m-%d") -> pd.DataFrame:
    out = df.copy()
    out.insert(0, "Date", pd.DatetimeIndex(dates).strftime(fmt))
    return out


def test_blank_rows_rejected_not_dropped(client):
    """40 fully blank rows must be an error, not a silent 300->260 trim."""
    df = _returns_frame(rows=300)
    df.loc[100:139, [f"s{i}" for i in range(5)]] = np.nan
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "missing values" in r.json()["detail"]


def test_intraday_and_offcalendar_dates_rejected(client):
    """Only daily (~1d spacing) or monthly (20-40d) uploads are supported."""
    base = _returns_frame(rows=300, dates=False)
    for freq, name in (("h", "hourly"), ("min", "minute"), ("W", "weekly")):
        d = pd.date_range("2024-01-01", periods=300, freq=freq)
        r = _post(client, _dated_rows(base, d, "%Y-%m-%d %H:%M"), 10)
        assert r.status_code == 400, name
        assert "supported calendar" in r.json()["detail"], name

    # two timestamps inside one day -> intraday, not daily
    d = pd.DatetimeIndex(
        list(pd.bdate_range("2020-01-01", periods=299)) + [pd.Timestamp("2020-01-01")])
    r = _post(client, _dated_rows(base, d), 10)
    assert r.status_code == 400


def test_per_column_numerical_guards(client):
    """Each column is assessed: a near-constant column mixed among real ones
    is a supported-range rejection, and |mean|/sd >= 1 is near-riskless."""
    df = _returns_frame(rows=300, dates=False, cols=4)
    df["const"] = 0.001
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "near-constant" in r.json()["detail"]

    rng = np.random.default_rng(0)
    df = _returns_frame(rows=300, dates=False, cols=4)
    df["cash"] = 0.001 + rng.normal(0, 1e-8, 300)
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "near-riskless" in r.json()["detail"]


def test_undated_frequency_disclosed_as_unverified(client):
    df = _returns_frame(dates=False)
    r = _post(client, df, 5, frequency="daily")
    assert r.status_code == 200, r.text
    a = r.json()["analysis"]
    assert a["frequency_verified"] is False
    assert any("could not be verified" in n for n in a["verdict"]["narrative"])

    # dated uploads verify the frequency
    a2 = _post(client, _returns_frame(dates=True), 5).json()["analysis"]
    assert a2["frequency_verified"] is True


def test_declared_below_observed_rejected(client):
    r = _post(client, _returns_frame(), 3)
    assert r.status_code == 400
    assert "smaller than" in r.json()["detail"]


def test_single_column_audit_rejected(client):
    # with one observed series the cross-trial Sharpe variance — and so the
    # declared-trial correction — is unestimable; abstain instead of
    # manufacturing a zero-variance threshold.
    r = _post(client, _returns_frame(cols=1), 100000)
    assert r.status_code == 400
    assert "at least 2 numeric return columns" in r.json()["detail"]


def test_missing_and_nonfinite_cells_rejected(client):
    df = _returns_frame()
    df.loc[10, "s1"] = np.nan
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "missing values" in r.json()["detail"]

    df = _returns_frame()
    df.loc[10, "s1"] = np.inf
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "finite" in r.json()["detail"]


def test_non_numeric_and_wrong_unit_columns_rejected(client):
    df = _returns_frame()
    df["label"] = ["0.01%"] * len(df)
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "non-numeric" in r.json()["detail"]

    df = _returns_frame()
    df.loc[10, "s1"] = 1.5  # -150% in one period: percent units or a bug,
    df.loc[11, "s2"] = -1.5  # not decimal returns; refuse, don't truncate
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "supported input range" in r.json()["detail"]


def test_degenerate_sharpe_variance_blocks_extrapolation(client):
    """Two near-identical columns declared as 100000 trials: the uploaded
    subset cannot estimate the cross-trial Sharpe variance, so the declared
    correction is unestimable — abstain rather than report DSR ~1."""
    rng = np.random.default_rng(20261001)
    base = rng.normal(0.0006, 0.01, 500)
    df = pd.DataFrame({"a": base, "b": base + rng.normal(0, 1e-5, 500)})
    df.insert(0, "Date", pd.bdate_range("2020-01-01", periods=500))
    r = _post(client, df, 100000)
    assert r.status_code == 400
    assert "unestimable" in r.json()["detail"]


def test_constant_column_sharpe_is_zero_not_astronomical():
    assert sharpe_ratio(np.full(500, 0.001)) == 0.0


def test_constant_matrix_rejected(client):
    df = _returns_frame()
    for c in ("s0", "s1", "s2", "s3", "s4"):
        df[c] = 0.001
    r = _post(client, df, 50)
    assert r.status_code == 400
    assert "constant" in r.json()["detail"]


def test_short_upload_rejected(client):
    r = _post(client, _returns_frame(rows=40), 50)
    assert r.status_code == 400


def test_declared_below_columns_rejected_in_library():
    df = _returns_frame(dates=False)
    with pytest.raises(ValueError, match="smaller than"):
        analyze_returns_matrix(df, declared_trials=3)


# --- benchmark: aligned by real dates or explicitly refused ------------------


def _monthly_frame(rows: int = 120, start: str = "2015-01-01") -> pd.DataFrame:
    rng = np.random.default_rng(7)
    df = pd.DataFrame({f"s{i}": rng.normal(0.002, 0.04, rows) for i in range(5)})
    df.insert(0, "Date", pd.date_range(start, periods=rows, freq="MS"))
    return df


def test_benchmark_aligned_on_uploaded_dates(client):
    df = _monthly_frame()
    r = _post(client, df, 12, benchmark="WB_GOLD", frequency="monthly")
    assert r.status_code == 200, r.text
    a = r.json()["analysis"]
    assert a["reality_check_p"] is not None
    assert a["frequency"] == "monthly" and a["periods_per_year"] == 12
    # the uploaded dates, not positional placeholders, label the equity curve
    assert a["equity_curves"]["dates"][0] == "2015-01-01"


def test_benchmark_never_silently_dropped(client):
    # no date column -> the benchmark cannot be aligned; refuse, don't omit
    df = _monthly_frame().drop(columns=["Date"])
    r = _post(client, df, 12, benchmark="WB_GOLD", frequency="monthly")
    assert r.status_code == 400
    assert "date column" in r.json()["detail"]

    # dates the benchmark calendar doesn't cover
    df = _monthly_frame(start="2090-01-01")
    r = _post(client, df, 12, benchmark="WB_GOLD", frequency="monthly")
    assert r.status_code == 400
    assert "overlaps only" in r.json()["detail"]

    # monthly benchmark against a daily upload -> frequency mismatch
    df = _returns_frame()
    r = _post(client, df, 50, benchmark="WB_GOLD")
    assert r.status_code == 400
    assert "not daily" in r.json()["detail"]


def test_benchmark_rejects_noncontiguous_upload(client):
    df = _monthly_frame().drop(index=[10, 11, 12]).reset_index(drop=True)
    r = _post(client, df, 12, benchmark="WB_GOLD", frequency="monthly")
    assert r.status_code == 400
    assert "not contiguous" in r.json()["detail"]


def test_benchmark_inner_join_matches_reference_rc(client):
    """Reviewer regression: a monthly 1996–2005 upload must be joined to the
    WB_GOLD rows for those months — the buggy code used the last len(df)
    rows (2016–2026) and produced RC p 0.974 vs the aligned 0.37."""
    from mirage.data import load_close
    from mirage.diagnostics.reality_check import reality_check

    win = load_close("WB_GOLD").pct_change().dropna().loc["1996-01":"2005-12"]
    rng = np.random.default_rng(20261001)
    df = pd.DataFrame({
        "Date": win.index.strftime("%Y-%m-%d"),
        "hold_gold": win.to_numpy(),
        "hold_gold_plus": win.to_numpy() + 0.002,
        "noise": rng.normal(0.0, 0.03, len(win)),
    })
    r = _post(client, df, 3, benchmark="WB_GOLD", frequency="monthly")
    assert r.status_code == 200, r.text
    expected = reality_check(
        df[["hold_gold", "hold_gold_plus", "noise"]].to_numpy(),
        win.to_numpy(), n_bootstrap=500, seed=0,
    ).p_value
    assert r.json()["analysis"]["reality_check_p"] == pytest.approx(
        expected, abs=0.05)


def test_declared_frequency_checked_against_dates(client):
    """Monthly-spaced dates uploaded as 'daily' must be refused — otherwise a
    monthly Sharpe is annualised as if daily (Sharpe 2.34 vs 0.51)."""
    df = _monthly_frame()
    r = _post(client, df, 12, frequency="daily")
    assert r.status_code == 400
    assert "look monthly" in r.json()["detail"]


def test_cli_audit_honours_benchmark_and_frequency(tmp_path, client):
    df = _monthly_frame()
    p = tmp_path / "m.csv"
    df.to_csv(p, index=False)
    res = CliRunner().invoke(
        cli.app, ["audit", str(p), "--trials", "12", "--benchmark", "WB_GOLD",
                  "--frequency", "monthly"])
    assert res.exit_code == 0, res.output
    out = json.loads(res.stdout)
    api = _post(client, df, 12, benchmark="WB_GOLD",
                frequency="monthly").json()["analysis"]
    assert out["reality_check_p"] == pytest.approx(api["reality_check_p"])

    # a benchmark on undated data is refused by the CLI, not silently omitted
    df.drop(columns=["Date"]).to_csv(p, index=False)
    res = CliRunner().invoke(
        cli.app, ["audit", str(p), "--trials", "12", "--benchmark", "WB_GOLD",
                  "--frequency", "monthly"])
    assert res.exit_code != 0
    assert "date column" in res.output
