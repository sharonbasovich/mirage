"""Abuse / hardening regression tests for the public HTTP API."""

from __future__ import annotations

import threading

import numpy as np
import pytest
from fastapi.testclient import TestClient

from mirage import api


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("MIRAGE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("MIRAGE_YAHOO_DIR", str(tmp_path / "no-yahoo"))
    return TestClient(api.app)


def _csv(rows: int, cols: int, seed: int = 0) -> bytes:
    r = np.random.default_rng(seed).normal(0, 0.01, (rows, cols))
    head = ",".join(f"s{i}" for i in range(cols))
    return (head + "\n" + "\n".join(",".join(f"{x:.5f}" for x in row) for row in r)).encode()


def test_public_demo_uses_bundled_worldbank_only(client):
    keys = {d["key"] for d in client.get("/api/demos").json()}
    assert keys == {"wb_gold_ma", "wb_brent_tsmom", "wb_commodity_mom", "wb_gold_rsi"}
    syms = client.get("/api/symbols").json()
    assert syms and all(s["license"] == "CC BY 4.0" for s in syms)


def test_run_generates_safe_program_id_and_roundtrips(client):
    r = client.post("/api/demo/wb_gold_ma")
    assert r.status_code == 200, r.text
    pid = r.json()["program_id"]
    assert api.PROGRAM_ID_RE.fullmatch(pid)
    assert r.json()["analysis"]["frequency"] == "monthly"
    assert client.get(f"/api/programs/{pid}/analysis").status_code == 200
    cert = client.get(f"/api/programs/{pid}/certificate").json()
    assert cert["trial_count"] == r.json()["analysis"]["n_trials"]
    assert "not a digital signature" in cert["integrity_note"]


def test_caller_supplied_program_id_rejected(client):
    body = {"family": "ma_cross", "symbols": ["WB_GOLD"], "program_id": "../../etc/passwd"}
    assert client.post("/api/run", json=body).status_code == 422


@pytest.mark.parametrize("pid", ["..%2F..%2Fetc%2Fpasswd", "a.b", "%2e%2e", "x" * 81, "a%00b"])
def test_path_traversal_program_ids_rejected(client, pid):
    for suffix in ("analysis", "trials", "certificate"):
        r = client.get(f"/api/programs/{pid}/{suffix}")
        assert r.status_code in (400, 404), (pid, suffix, r.status_code)
    with pytest.raises(Exception):  # noqa: B017
        api._analysis_path("../evil")


def test_oversized_grid_rejected(client):
    too_many_values = {"fast": list(range(1, 14)), "slow": [20], "long_only": [True]}
    r = client.post("/api/run", json={"family": "ma_cross", "symbols": ["WB_GOLD"],
                                      "grid": too_many_values})
    assert r.status_code == 400
    too_many_trials = {"fast": list(range(1, 13)), "slow": list(range(20, 32)),
                       "long_only": [True]}
    r = client.post("/api/run", json={"family": "ma_cross", "symbols": ["WB_GOLD"],
                                      "grid": too_many_trials})
    assert r.status_code == 413
    huge_window = {"fast": [2], "slow": [10**9], "long_only": [True]}
    r = client.post("/api/run", json={"family": "ma_cross", "symbols": ["WB_GOLD"],
                                      "grid": huge_window})
    assert r.status_code == 400
    unknown_key = {"fast": [2], "slow": [12], "evil": [1]}
    r = client.post("/api/run", json={"family": "ma_cross", "symbols": ["WB_GOLD"],
                                      "grid": unknown_key})
    assert r.status_code == 400


def test_run_input_bounds(client):
    base = {"family": "ma_cross", "symbols": ["WB_GOLD"]}
    assert client.post("/api/run", json={**base, "cost_bps": 1e9}).status_code == 422
    assert client.post("/api/run", json={**base, "symbols": ["WB_GOLD"] * 13}).status_code == 422
    assert client.post("/api/run", json={**base, "symbols": ["../x"]}).status_code == 400
    assert client.post("/api/run", json={"family": "nope", "symbols": ["WB_GOLD"]}).status_code == 400


def test_concurrent_run_limit(client, monkeypatch):
    held = [api._run_slots.acquire(blocking=False) for _ in range(api.MAX_CONCURRENT_RUNS)]
    try:
        assert all(held)
        r = client.post("/api/demo/wb_gold_ma")
        assert r.status_code == 429
        assert r.headers.get("retry-after") == "5"
    finally:
        for _ in held:
            api._run_slots.release()
    assert client.post("/api/demo/wb_gold_ma").status_code == 200


def test_concurrent_runs_never_exceed_cap(client, monkeypatch):
    active = 0
    peak = 0
    lock = threading.Lock()
    gate = threading.Event()
    real = api.run_program

    def slow_run_program(*a, **k):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        gate.wait(5)
        with lock:
            active -= 1
        return real(*a, **k)

    monkeypatch.setattr(api, "run_program", slow_run_program)
    codes: list[int] = []
    threads = [threading.Thread(target=lambda: codes.append(
        client.post("/api/demo/wb_gold_ma").status_code)) for _ in range(5)]
    for t in threads:
        t.start()
    for _ in range(50):
        if len(codes) >= 5 - api.MAX_CONCURRENT_RUNS:
            break
        threading.Event().wait(0.1)
    gate.set()
    for t in threads:
        t.join(30)
    assert peak <= api.MAX_CONCURRENT_RUNS
    assert codes.count(429) >= 5 - api.MAX_CONCURRENT_RUNS


def test_audit_accepts_bounded_upload(client):
    r = client.post("/api/audit", files={"file": ("r.csv", _csv(300, 5), "text/csv")},
                    data={"n_trials": "50"})
    assert r.status_code == 200, r.text
    assert r.json()["analysis"]["declared_trials"] == 50


def test_audit_oversized_upload_rejected(client):
    big = b"a\n" + b"0.001\n" * (api.MAX_UPLOAD_BYTES // 6 + 10)
    r = client.post("/api/audit", files={"file": ("r.csv", big, "text/csv")},
                    data={"n_trials": "10"})
    assert r.status_code == 413


def test_audit_row_and_column_limits(client):
    r = client.post("/api/audit",
                    files={"file": ("r.csv", _csv(api.MAX_AUDIT_ROWS + 5, 1), "text/csv")},
                    data={"n_trials": "10"})
    assert r.status_code == 413
    r = client.post("/api/audit",
                    files={"file": ("r.csv", _csv(100, api.MAX_AUDIT_COLUMNS + 5), "text/csv")},
                    data={"n_trials": "10"})
    assert r.status_code == 413


@pytest.mark.parametrize("n", ["0", "-5", str(api.MAX_DECLARED_TRIALS + 1), "10000000000000"])
def test_audit_large_or_invalid_n_trials_rejected(client, n):
    r = client.post("/api/audit", files={"file": ("r.csv", _csv(100, 2), "text/csv")},
                    data={"n_trials": n})
    assert r.status_code == 422


def test_no_wildcard_cors_by_default(client):
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}


def test_spa_does_not_serve_files_outside_dist(client):
    r = client.get("/..%2F..%2Fpyproject.toml")
    assert "setuptools" not in r.text
