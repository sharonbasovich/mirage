"""Tamper-evident Trial Ledger (SQLite, hash-chained).

Every backtest run appends an entry recording the research program, the
strategy config hash, the data hash, metrics and a pointer to the previous
entry's hash.  Any edit to history breaks the chain, which ``verify_chain``
detects.  The ledger powers "pre-registration for backtests": the Deflated
Sharpe Ratio uses the *recorded* trial count, which cannot be silently
forgotten.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "ledger.sqlite3"

GENESIS = "0" * 64


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def config_hash(config: dict) -> str:
    return _sha(json.dumps(config, sort_keys=True, default=str))


@dataclass
class LedgerEntry:
    id: int
    ts: float
    program_id: str
    label: str
    config: dict
    config_hash: str
    data_hash: str
    metrics: dict
    returns_sha: str
    prev_hash: str
    entry_hash: str


class Ledger:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _init(self) -> None:
        with self._conn() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS entries(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    program_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    data_hash TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    returns_sha TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_prog ON entries(program_id)")

    def _head(self, con: sqlite3.Connection) -> str:
        row = con.execute("SELECT entry_hash FROM entries ORDER BY id DESC LIMIT 1").fetchone()
        return row["entry_hash"] if row else GENESIS

    def append(
        self,
        program_id: str,
        label: str,
        config: dict,
        data_hash: str,
        metrics: dict,
        returns_sha: str,
    ) -> LedgerEntry:
        ts = time.time()
        with self._conn() as con:
            prev = self._head(con)
            ch = config_hash(config)
            cfg_json = json.dumps(config, sort_keys=True, default=str)
            met_json = json.dumps(metrics, sort_keys=True, default=str)
            payload = "|".join(
                [str(ts), program_id, label, cfg_json, ch, data_hash, met_json, returns_sha, prev]
            )
            eh = _sha(payload)
            cur = con.execute(
                """INSERT INTO entries
                   (ts, program_id, label, config_json, config_hash, data_hash,
                    metrics_json, returns_sha, prev_hash, entry_hash)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (ts, program_id, label, cfg_json, ch, data_hash, met_json, returns_sha, prev, eh),
            )
            eid = int(cur.lastrowid or 0)
        return LedgerEntry(eid, ts, program_id, label, config, ch, data_hash,
                           metrics, returns_sha, prev, eh)

    def _row_to_entry(self, row: sqlite3.Row) -> LedgerEntry:
        return LedgerEntry(
            id=row["id"],
            ts=row["ts"],
            program_id=row["program_id"],
            label=row["label"],
            config=json.loads(row["config_json"]),
            config_hash=row["config_hash"],
            data_hash=row["data_hash"],
            metrics=json.loads(row["metrics_json"]),
            returns_sha=row["returns_sha"],
            prev_hash=row["prev_hash"],
            entry_hash=row["entry_hash"],
        )

    def entries(self, program_id: str | None = None) -> list[LedgerEntry]:
        with self._conn() as con:
            if program_id:
                rows = con.execute(
                    "SELECT * FROM entries WHERE program_id=? ORDER BY id", (program_id,)
                ).fetchall()
            else:
                rows = con.execute("SELECT * FROM entries ORDER BY id").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def programs(self) -> list[dict[str, Any]]:
        with self._conn() as con:
            rows = con.execute(
                """SELECT program_id, COUNT(*) n, MIN(ts) first_ts, MAX(ts) last_ts
                   FROM entries GROUP BY program_id ORDER BY last_ts DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def trial_count(self, program_id: str) -> int:
        with self._conn() as con:
            row = con.execute(
                "SELECT COUNT(*) c FROM entries WHERE program_id=?", (program_id,)
            ).fetchone()
        return int(row["c"])

    def verify_chain(self) -> tuple[bool, str]:
        """Re-walk the chain; returns (ok, message)."""
        prev = GENESIS
        for e in self.entries():
            payload = "|".join(
                [
                    str(e.ts),
                    e.program_id,
                    e.label,
                    json.dumps(e.config, sort_keys=True, default=str),
                    e.config_hash,
                    e.data_hash,
                    json.dumps(e.metrics, sort_keys=True, default=str),
                    e.returns_sha,
                    e.prev_hash,
                ]
            )
            if _sha(payload) != e.entry_hash:
                return False, f"entry {e.id} hash mismatch"
            if e.prev_hash != prev:
                return False, f"entry {e.id} prev_hash mismatch"
            prev = e.entry_hash
        return True, "chain intact"

    def export_certificate(self, program_id: str, verdict: dict | None = None) -> dict:
        """Backtest Pre-registration Certificate for a program."""
        entries = self.entries(program_id)
        ok, msg = self.verify_chain()
        best = max(entries, key=lambda e: e.metrics.get("sharpe", float("-inf")), default=None)
        return {
            "certificate": "mirage-pre-registration",
            "version": 1,
            "program_id": program_id,
            "issued_at": time.time(),
            "trial_count": len(entries),
            "first_trial_ts": entries[0].ts if entries else None,
            "last_trial_ts": entries[-1].ts if entries else None,
            "chain_head": entries[-1].entry_hash if entries else GENESIS,
            "chain_valid": ok,
            "chain_message": msg,
            "best_trial": (
                {
                    "entry_id": best.id,
                    "label": best.label,
                    "config": best.config,
                    "metrics": best.metrics,
                }
                if best
                else None
            ),
            "verdict": verdict,
            "disclaimer": "Research prototype built for GIBC V2. Not a product, "
            "not a financial service, not financial advice.",
        }


def new_program_id(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:8]}"
