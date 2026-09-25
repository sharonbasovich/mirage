"""Run all self-validation experiments: `python -m experiments.run_all`."""

from __future__ import annotations


def main(only: str | None = None) -> None:
    if only in (None, "e1"):
        from experiments import e1_false_positives

        e1_false_positives.run()
    if only in (None, "e2"):
        from experiments import e2_power

        e2_power.run()
    if only in (None, "e3"):
        from experiments import e3_real_strategies

        e3_real_strategies.run()


if __name__ == "__main__":
    import sys

    main(only=sys.argv[1] if len(sys.argv) > 1 else None)
