"""CLI for running FX rates backfill."""

from __future__ import annotations

import click
from flask.cli import with_appcontext

from app.services.backfill import run_backfill


@click.command("backfill-rates")
@click.option("--days", default=30, show_default=True, help="Number of days to backfill")
@click.option("--base", default="USD", show_default=True, help="Canonical base currency")
@with_appcontext
def backfill_rates(days: int, base: str) -> None:
    """Backfill historical FX rates for the specified period."""

    click.echo(f"Starting backfill for {days} days with base {base.upper()}...")
    run_backfill(days=days, base_currency=base)
    click.echo("Backfill completed.")
