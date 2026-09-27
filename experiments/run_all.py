"""Run all self-validation experiments: `python -m experiments.run_all`."""

from __future__ import annotations

from mirage.data import is_available

YAHOO_NEEDED = {"e1": ["SPY"], "e3": ["SPY", "BTC-USD", "XLK"]}


def _yahoo_ready(name: str) -> bool:
    ok = all(is_available(s) for s in YAHOO_NEEDED[name])
    if not ok:
        print(f"skipping {name}: needs locally fetched Yahoo data "
              f"(run `python scripts/fetch_data.py`)")
    return ok


def main(only: str | None = None) -> None:
    if only in (None, "e1") and _yahoo_ready("e1"):
        from experiments import e1_false_positives

        e1_false_positives.run()
    if only in (None, "e2"):
        from experiments import e2_power

        e2_power.run()
    if only in (None, "e3") and _yahoo_ready("e3"):
        from experiments import e3_real_strategies

        e3_real_strategies.run()
    if only in (None, "e4"):
        from experiments import e4_worldbank

        e4_worldbank.run()


if __name__ == "__main__":
    import sys

    main(only=sys.argv[1] if len(sys.argv) > 1 else None)
