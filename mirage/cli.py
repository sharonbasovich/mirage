"""Mirage CLI: run grids, audit external returns, report verdicts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import typer

from mirage.audit import AuditInputError, prepare_audit_frame
from mirage.ledger import Ledger
from mirage.program import analyze_returns_matrix, analyze_trials, run_program
from mirage.strategies import STRATEGIES

app = typer.Typer(help="Mirage - the backtest lie detector", no_args_is_help=True)


def _parse_grid(grid: str | None) -> dict | None:
    """'fast=5,10;slow=100,200' -> {'fast': [5,10], 'slow': [100,200]}."""
    if not grid:
        return None
    out: dict[str, list] = {}
    for part in grid.split(";"):
        if not part.strip():
            continue
        k, vs = part.split("=")
        vals: list[int | float | bool | str] = []
        for v in vs.split(","):
            v = v.strip()
            try:
                vals.append(int(v))
            except ValueError:
                try:
                    vals.append(float(v))
                except ValueError:
                    vals.append(v in ("true", "True") if v in ("true", "false", "True", "False") else v)
        out[k.strip()] = vals
    return out


@app.command()
def run(
    family: str = typer.Argument(..., help=f"strategy family: {sorted(STRATEGIES)}"),
    symbols: str = typer.Option("WB_GOLD", help="comma-separated symbols (WB_* bundled; Yahoo after fetch)"),
    grid: str | None = typer.Option(None, help="e.g. 'fast=5,10;slow=100,200'"),
    cost_bps: float = typer.Option(5.0),
    program: str | None = typer.Option(None, help="existing program id to append to"),
    analyze: bool = typer.Option(True, help="run diagnostics after trials"),
):
    """Run a parameter grid; every trial is appended to the hash-chained ledger."""
    syms = [s.strip() for s in symbols.split(",")]
    pid, trials = run_program(
        family, syms, grid=_parse_grid(grid), cost_bps=cost_bps,
        program_id=program,
    )
    typer.echo(f"program {pid}: {len(trials)} trials logged")
    if analyze:
        res = analyze_trials(trials)
        v = res["verdict"]
        typer.echo(json.dumps({
            "best": res["best_label"], "sharpe": res["best_sharpe"],
            "dsr": res["dsr"], "pbo": res["pbo"],
            "score": v["score"], "verdict": v["label"],
        }, indent=2))


@app.command()
def audit(
    csv: Path = typer.Argument(..., help="CSV of returns; one column per trial"),
    trials: int = typer.Option(..., "--trials", "-n", help="declared total trials tried"),
    benchmark: str | None = typer.Option(None, help="symbol to use as benchmark"),
    date_col: str = typer.Option("Date", help="date column for benchmark alignment"),
    frequency: str = typer.Option("daily", help="return frequency: daily|monthly"),
    cost_bps: float = typer.Option(5.0, help="assumed transaction cost, basis points"),
):
    """Audit an external backtest: upload returns + declared trial count."""
    try:
        raw = pd.read_csv(csv)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"could not parse CSV: {exc}", err=True)
        raise typer.Exit(1) from exc
    try:
        prep = prepare_audit_frame(
            raw, declared_trials=trials, frequency=frequency,
            date_col=date_col, benchmark=benchmark,
        )
    except AuditInputError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    ppy = 12 if frequency == "monthly" else 252
    try:
        res = analyze_returns_matrix(
            prep.returns, benchmark_returns=prep.benchmark,
            assumed_cost_bps=cost_bps, periods_per_year=ppy,
            declared_trials=trials, frequency_verified=prep.has_dates,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    out = {
        "best": res["best_label"], "sharpe": res["best_sharpe"],
        "psr": res["psr"], "dsr": res["dsr"], "pbo": res["pbo"],
        "reality_check_p": res["reality_check_p"],
        "n_trials": res["n_trials"], "observed_trials": res["observed_trials"],
        "benchmark_dropped_rows": prep.benchmark_dropped,
        "frequency_verified": res["frequency_verified"],
        "score": res["verdict"]["score"], "verdict": res["verdict"]["label"],
        "label_capped": res["verdict"]["label_capped"],
        "narrative": res["verdict"]["narrative"],
    }
    typer.echo(json.dumps(out, indent=2))


@app.command()
def report(
    program: str = typer.Argument(..., help="program id"),
    out: Path | None = typer.Option(None, help="write certificate JSON here"),
):
    """Print the (unsigned) trial-ledger certificate for a recorded program."""
    led = Ledger()
    entries = led.entries(program)
    if not entries:
        typer.echo(f"no entries for program {program}", err=True)
        raise typer.Exit(1)
    cert = led.export_certificate(program)
    cert["data_hash"] = entries[-1].data_hash
    text = json.dumps(cert, indent=2, default=str)
    if out:
        out.write_text(text)
        typer.echo(f"wrote {out}")
    else:
        typer.echo(text)


@app.command()
def programs():
    """List recorded research programs."""
    for p in Ledger().programs():
        typer.echo(f"{p['program_id']}  trials={p['n']}")


@app.command()
def experiments(
    only: str | None = typer.Option(None, help="e1|e2|e3|e4"),
):
    """Run the self-validation experiments (writes reports/)."""
    from experiments.run_all import main as run_all

    run_all(only=only)


if __name__ == "__main__":
    app()
