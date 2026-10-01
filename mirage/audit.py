"""Shared audit-input preparation for the API endpoint and the CLI.

One normalization path for both front ends: an uploaded returns CSV becomes a
validated ``PreparedAudit`` *before* any diagnostic runs, so the API and CLI
cannot disagree about what was accepted or how the benchmark was aligned.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mirage.data import is_available, load_close, source_info

MIN_AUDIT_ROWS = 64
DATE_COLUMN_CANDIDATES = ("date", "timestamp", "time")
# median spacing between uploaded dates (days) that identifies each frequency;
# anything else (weekly, quarterly, irregular) is unsupported, not guessed at
_FREQUENCY_SPACING_DAYS = {"daily": 3.0, "monthly": (20.0, 40.0)}


class AuditInputError(ValueError):
    """Invalid audit upload; the API maps this to HTTP 400."""


@dataclass
class PreparedAudit:
    returns: pd.DataFrame
    benchmark: pd.Series | None
    benchmark_dropped: int = 0  # uploaded rows outside benchmark coverage


def _date_column(df: pd.DataFrame, date_col: str | None) -> str | None:
    if date_col is not None and date_col in df.columns:
        return date_col
    for c in df.columns:
        if str(c).strip().lower() in DATE_COLUMN_CANDIDATES:
            return str(c)
    return None


def _median_spacing_days(dates: pd.DatetimeIndex) -> float:
    gaps = np.diff(dates.asi8) / 86_400e9
    return float(np.median(gaps))


def _infer_frequency(dates: pd.DatetimeIndex) -> tuple[str | None, float]:
    med = _median_spacing_days(dates)
    lo, hi = _FREQUENCY_SPACING_DAYS["monthly"]
    if med <= _FREQUENCY_SPACING_DAYS["daily"]:
        return "daily", med
    if lo <= med <= hi:
        return "monthly", med
    return None, med


def _align_benchmark(
    benchmark: str,
    dates: pd.DatetimeIndex | None,
    frequency: str,
    min_rows: int,
) -> tuple[np.ndarray, pd.Series]:
    """Return ``(row mask, per-period benchmark returns)`` inner-joined on dates.

    Joined dates must be consecutive entries in the benchmark calendar —
    otherwise uploaded and benchmark return intervals would differ and the
    comparison would be invented.  The caller drops unmasked uploaded rows.
    """
    if not is_available(benchmark):
        raise AuditInputError(f"benchmark {benchmark!r} is not available")
    if source_info(benchmark)["frequency"] != frequency:
        raise AuditInputError(f"benchmark {benchmark!r} is not {frequency} data")
    if dates is None:
        raise AuditInputError(
            "a benchmark requires a usable date column in the upload "
            "(named 'date', 'timestamp' or 'time')"
        )
    ret = load_close(benchmark).pct_change()
    if frequency == "monthly":
        keys = dates.to_period("M")
        ret.index = ret.index.to_period("M")
    else:
        keys = dates.normalize()
        ret.index = ret.index.normalize()
    keep = np.asarray(keys.isin(ret.index))
    if int(keep.sum()) < min_rows:
        raise AuditInputError(
            f"benchmark {benchmark!r} overlaps only {int(keep.sum())} of the "
            f"uploaded dates (need >= {min_rows})"
        )
    pos = ret.index.get_indexer(keys[keep])
    if len(pos) > 1 and not np.all(np.diff(pos) == 1):
        raise AuditInputError(
            "the uploaded dates are not contiguous in the benchmark calendar; "
            "per-period comparison is only defined for consecutive periods"
        )
    b = ret.iloc[pos]
    if b.isna().any():
        raise AuditInputError(
            f"benchmark {benchmark!r} has no earlier close for the first "
            "aligned uploaded date; the benchmark series must start before it"
        )
    return keep, pd.Series(b.to_numpy(dtype=float))


def prepare_audit_frame(
    raw: pd.DataFrame,
    *,
    declared_trials: int,
    frequency: str = "daily",
    date_col: str | None = None,
    benchmark: str | None = None,
    min_rows: int = MIN_AUDIT_ROWS,
) -> PreparedAudit:
    """Validate an uploaded returns frame into a ``PreparedAudit``.

    Raises ``AuditInputError`` with a user-readable message for every
    rejection — gaps are ambiguous returns and are never silently filled,
    non-numeric columns are never silently dropped, and a requested benchmark
    is never silently omitted.
    """
    if frequency not in ("daily", "monthly"):
        raise AuditInputError("frequency must be 'daily' or 'monthly'")
    if declared_trials < 1:
        raise AuditInputError("declared trial count must be at least 1")

    df = raw.copy()
    dates: pd.DatetimeIndex | None = None
    dc = _date_column(df, date_col)
    if dc is not None:
        parsed = pd.to_datetime(df[dc], errors="coerce")
        if parsed.isna().any():
            raise AuditInputError(f"could not parse dates in column {dc!r}")
        dates = pd.DatetimeIndex(parsed)
        df = df.drop(columns=[dc])

    non_numeric = [str(c) for c, t in df.dtypes.items() if not np.issubdtype(t, np.number)]
    if non_numeric:
        raise AuditInputError(
            "non-numeric columns cannot be audited as returns: "
            + ", ".join(non_numeric[:5])
            + ("..." if len(non_numeric) > 5 else "")
            + " — remove them or convert values to decimal returns"
        )

    nonempty = df.notna().any(axis=1)
    df = df.loc[nonempty]
    if dates is not None:
        dates = dates[nonempty.to_numpy()]
    if df.shape[1] == 0 or len(df) == 0:
        raise AuditInputError("no numeric return columns found")
    bad_cols = [str(c) for c in df.columns[df.isna().any(axis=0)]]
    if bad_cols:
        raise AuditInputError(
            "return columns contain missing values: "
            + ", ".join(bad_cols[:5])
            + ("..." if len(bad_cols) > 5 else "")
        )
    if not np.isfinite(df.to_numpy(dtype=float)).all():
        raise AuditInputError("returns must be finite numbers")
    if (df.abs() >= 1.0).any().any():
        raise AuditInputError(
            "returns must be decimals; values |r| >= 1 (>=100% per period) "
            "look like percent units or price levels, not returns"
        )
    if df.shape[1] < 2:
        raise AuditInputError(
            "need at least 2 numeric return columns (one per tried "
            "configuration); a single series cannot support a "
            "multiple-testing audit"
        )
    if len(df) < min_rows:
        raise AuditInputError(f"need at least {min_rows} rows of returns")
    if not (df.std(ddof=1) > 1e-10).any():
        raise AuditInputError("every return column is constant; nothing to audit")
    if declared_trials < df.shape[1]:
        raise AuditInputError(
            f"declared trial count {declared_trials} is smaller than the "
            f"{df.shape[1]} uploaded return columns"
        )

    if dates is not None:
        if dates.has_duplicates:
            raise AuditInputError("duplicate dates in the upload")
        order = dates.argsort()
        df = df.iloc[order]
        dates = dates[order]
        df.index = pd.DatetimeIndex(dates)
        inferred, med = _infer_frequency(dates)
        if inferred is None:
            raise AuditInputError(
                f"uploaded dates have a median spacing of {med:.0f} days; "
                "audits support daily or monthly returns"
            )
        if inferred != frequency:
            raise AuditInputError(
                f"uploaded dates look {inferred} (median spacing {med:.0f} "
                f"days) but frequency={frequency!r} was declared"
            )
    else:
        df.index = pd.RangeIndex(len(df))

    bench = None
    dropped = 0
    if benchmark:
        keep, b = _align_benchmark(benchmark, dates, frequency, min_rows)
        dropped = int((~keep).sum())
        df = df.iloc[keep]
        b.index = df.index
        bench = b
    return PreparedAudit(returns=df, benchmark=bench, benchmark_dropped=dropped)
