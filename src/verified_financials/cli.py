"""``vfin`` command-line interface."""

from __future__ import annotations

from decimal import Decimal

import typer

from . import datagen
from ._env import load_env
from .config.loader import load_config
from .engines.borrowing_base import compute_borrowing_base
from .engines.fccr import compute_fccr
from .engines.verification import run_verification
from .pipeline import ingest, load_scenario, new_run_id, run_pipeline
from .store.db import connect, init_schema
from .store.repository import FactRepository

load_env()  # pick up <repo-root>/.env (e.g. OPENAI_API_KEY) for the CLI too

app = typer.Typer(add_completion=False, help="Sentinel — verification, borrowing base, FCCR.")


def _money(v) -> str:
    d = Decimal(str(v))
    sign = "-" if d < 0 else ""
    return f"{sign}${abs(d):,.2f}"


_SCENARIO_OPT = typer.Option("baseline", help="Scenario: baseline | stress")


def _repo_from_data(scenario: str = "baseline"):
    config = load_scenario(scenario)
    conn = connect(":memory:")
    init_schema(conn)
    repo = FactRepository(conn)
    ingest(repo, config, config.settings.data_dir)
    return repo, config


@app.command("generate-data")
def generate_data(seed: int = typer.Option(None, help="Override the config random seed.")):
    """Generate the synthetic dataset into the data directory."""
    paths = datagen.generate(seed=seed)
    for name, path in paths.items():
        typer.echo(f"  wrote {name:28} -> {path}")
    typer.secho("Synthetic data generated.", fg=typer.colors.GREEN)


@app.command("init-db")
def init_db():
    """Create the SQLite schema at the configured database path."""
    config = load_config()
    conn = connect(config.settings.database_path)
    init_schema(conn)
    typer.secho(f"Initialized database at {config.settings.database_path}", fg=typer.colors.GREEN)


@app.command()
def load():
    """Ingest the CSVs into the configured database as facts."""
    config = load_config()
    conn = connect(config.settings.database_path)
    init_schema(conn)
    n = ingest(FactRepository(conn), config)
    typer.secho(f"Loaded {n} facts into {config.settings.database_path}", fg=typer.colors.GREEN)


@app.command()
def verify(scenario: str = _SCENARIO_OPT):
    """Run the verification / tie-out engine and print findings."""
    repo, config = _repo_from_data(scenario)
    report = run_verification(repo, config, new_run_id())
    typer.secho("\nVERIFICATION / TIE-OUT", bold=True)
    for f in report.findings:
        color = typer.colors.GREEN if f.status == "pass" else typer.colors.RED
        tag = "PASS" if f.status == "pass" else f.severity.upper()
        typer.secho(f"  [{tag:>8}] {f.label}", fg=color)
        typer.echo(f"            {f.message}")
    typer.echo(f"\n  {report.passed} passed, {report.failed} exception(s).")


@app.command("borrowing-base")
def borrowing_base(scenario: str = _SCENARIO_OPT):
    """Compute the borrowing base and print the certificate summary."""
    repo, config = _repo_from_data(scenario)
    c = compute_borrowing_base(repo, config, new_run_id())
    typer.secho("\nBORROWING BASE CERTIFICATE", bold=True)
    for a, title in ((c.accounts_receivable, "Accounts Receivable"), (c.inventory, "Inventory")):
        typer.secho(f"  {title}", bold=True)
        typer.echo(f"    Gross            {_money(a.gross):>18}")
        for line in a.ineligibles:
            typer.echo(f"    less {line.label[:30]:30} ({_money(line.amount)})")
        for cl in a.concentration:
            typer.echo(f"    less concentration {cl.customer[:20]:20} ({_money(cl.excess_excluded)})")
        typer.echo(f"    Eligible         {_money(a.eligible):>18}")
        typer.echo(f"    Availability @{a.advance_rate:.0%}  {_money(a.availability):>14}")
    typer.echo(f"\n  Gross availability   {_money(c.gross_availability):>18}")
    typer.echo(f"  Borrowing base       {_money(c.borrowing_base):>18}  (binding: {c.binding_constraint})")
    typer.echo(f"  Less outstanding     ({_money(c.outstanding)})")
    typer.secho(f"  Excess availability  {_money(c.excess_availability):>18}", fg=typer.colors.CYAN, bold=True)


@app.command()
def fccr(scenario: str = _SCENARIO_OPT):
    """Compute the TTM FCCR and print the covenant summary."""
    repo, config = _repo_from_data(scenario)
    run_id = new_run_id()
    cert = compute_borrowing_base(repo, config, run_id)  # for springing excess availability
    r = compute_fccr(repo, config, run_id, excess_availability=cert.excess_availability)
    typer.secho("\nFCCR COVENANT (TTM)", bold=True)
    typer.echo(f"  Numerator (FCC-adj EBITDA)  {_money(r.numerator):>18}")
    typer.echo(f"  Denominator (fixed charges) {_money(r.denominator):>18}")
    typer.echo(f"  FCCR                        {r.fccr:>17}x   covenant {r.covenant}x")
    typer.echo(f"  Headroom                    {r.headroom_abs}x / {r.headroom_pct:.2%}")
    typer.echo("  Trend  " + "  ".join(f"{p.quarter}:{p.fccr}x" for p in r.trend))
    if r.springing_enabled:
        state = "ACTIVE" if r.covenant_active else "DORMANT"
        typer.echo(f"  Springing covenant          {state} (trigger {_money(r.springing_trigger)}, "
                   f"excess avail {_money(r.excess_availability)})")
    if r.equity_cure_enabled and r.covenant_active and not r.in_compliance:
        typer.echo(f"  Equity cure to restore      {_money(r.equity_cure_needed)}")
    status = "IN COMPLIANCE" if r.in_compliance else "BREACH"
    color = typer.colors.GREEN if r.in_compliance and not r.early_warning else typer.colors.YELLOW
    typer.secho(f"  Status: {status}" + ("  [EARLY WARNING]" if r.early_warning else ""), fg=color, bold=True)
    for reason in r.warning_reasons:
        typer.echo(f"    ! {reason}")


@app.command("run-all")
def run_all(
    generate: bool = typer.Option(True, help="Regenerate synthetic data first."),
    scenario: str = _SCENARIO_OPT,
):
    """Generate data, ingest, run all engines, and write artifacts (the demo button)."""
    config = load_scenario(scenario)
    if generate:
        datagen.generate(scenario=scenario)
        typer.echo(f"  synthetic data generated ({scenario})")
    result = run_pipeline(config=config, render=True)
    s = result.summary()
    typer.secho(f"\n=== Sentinel — run {result.run_id} ===", bold=True)
    typer.echo(f"  facts ingested        {s['fact_count']}")
    typer.echo(f"  verification          {s['verification']['passed']} passed, "
               f"{s['verification']['failed']} exception(s)")
    typer.echo(f"  borrowing base        {_money(result.certificate.borrowing_base)}")
    typer.echo(f"  excess availability   {_money(result.certificate.excess_availability)}")
    typer.echo(f"  FCCR                  {result.fccr.fccr}x (covenant {result.fccr.covenant}x)"
               + ("  [EARLY WARNING]" if result.fccr.early_warning else ""))
    typer.secho("\n  artifacts:", bold=True)
    for name, path in result.artifacts.items():
        typer.echo(f"    {path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
