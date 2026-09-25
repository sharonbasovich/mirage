"""Mirage CLI: run grids, audit external returns, report verdicts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import typer

from mirage.data import SYMBOLS, data_hash
from mirage.ledger import Ledger, new_program_id
from mirage.program import TrialResult, analyze_returns_matrix, analyze_trials, run_program
from mirage.strategies import STRATEGIES

app = typer.Typer(help="Mirage - the backtest lie detector", no_args_is_help=True)


def _parse_grid(grid: Optional[str]) -> dict | None:
    """'fast=5,10;slow=100,200' -> {'fast': [5,10], 'slow': [100,200]}."""
    if not grid:
        return None
    out: dict[str, list] = {}
    for part in grid.split(";"):
        if not part.strip():
            continue
        k, vs = part.split("=")
        vals = []
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
    symbols: str = typer.Option("SPY", help="comma-separated symbols"),
    grid: Optional[str] = typer.Option(None, help="e.g. 'fast=5,10;slow=100,200'"),
    cost_bps: float = typer.Option(5.0),
    program: Optional[str] = typer.Option(None, help="existing program id to append to"),
    analyze: bool = typer.Option(True, help="run diagnostics after trials"),
):
    """Run a parameter grid; every trial lands in the tamper-evident ledger."""
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
    csv: Path = typer.Argument(..., help="CSV of daily returns; one column per trial"),
    trials: int = typer.Option(..., "--trials", "-n", help="declared total trials tried"),
    benchmark: Optional[str] = typer.Option(None, help="symbol to use as benchmark"),
    date_col: str = typer.Option("Date"),
):
    """Audit an external backtest: upload returns + declared trial count."""
    df = pd.read_csv(csv)
    if date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col)
    df = df.select_dtypes(include=[np.number]).dropna(how="all").fillna(0.0)
    if df.shape[1] < 2:
        typer.echo("need at least 2 numeric columns (trials)", err=True)
        raise typer.Exit(1)

    # honor the declared total trial count even if only the best is uploaded:
    # if columns < declared, replicate padded noise columns are NOT used —
    # instead we pass n_trials to DSR via trial_sharpes length check below.
    res = analyze_returns_matrix(df)
    if trials > df.shape[1]:
        # rescale the DSR threshold to the *declared* number of trials
        from mirage.diagnostics.sharpe import dsr_expected_max_sharpe, psr, sharpe_ratio

        sharpes = np.array([sharpe_ratio(df[c].to_numpy()) for c in df.columns])
        best_col = res["best_label"]
        thr = dsr_expected_max_sharpe(sharpes, n_trials=trials)
        res["dsr"] = psr(df[best_col].to_numpy(), sr_benchmark=thr)
        res["dsr_threshold"] = thr
        res["n_trials"] = trials
    typer.echo(json.dumps({
        "best": res["best_label"], "sharpe": res["best_sharpe"],
        "psr": res["psr"], "dsr": res["dsr"], "pbo": res["pbo"],
        "reality_check_p": res["reality_check_p"],
        "score": res["verdict"]["score"], "verdict": res["verdict"]["label"],
        "narrative": res["verdict"]["narrative"],
    }, indent=2))


@app.command()
def report(
    program: str = typer.Argument(..., help="program id"),
    out: Optional[Path] = typer.Option(None, help="write certificate JSON here"),
):
    """Print the pre-registration certificate for a recorded program."""
    led = Ledger()
    entries = led.entries(program)
    if not entries:
        typer.echo(f"no entries for program {program}", err=True)
        raise typer.Exit(1)
    cert = led.export_certificate(program)
    cert["data_hash"] = data_hash(SYMBOLS)
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
    only: Optional[str] = typer.Option(None, help="e1|e2|e3"),
):
    """Run the self-validation experiments (writes reports/)."""
    from experiments.run_all import main as run_all

    run_all(only=only)


if __name__ == "__main__":
    app()
