"""CLI for running FX rates backfill."""

from __future__ import annotations

import click

from app.services.backfill import run_backfill


@click.group()
def cli():
    """Top-level CLI group."""


@cli.command()
@click.option("--days", default=30, show_default=True, help="Number of days to backfill")
@click.option("--base", default="USD", show_default=True, help="Canonical base currency")
def backfill_rates(days: int, base: str):
    """Backfill historical FX rates for the specified period."""

    click.echo(f"Starting backfill for {days} days with base {base.upper()}...")
    run_backfill(days=days, base_currency=base)
    click.echo("Backfill completed.")


if __name__ == "__main__":
    cli()
