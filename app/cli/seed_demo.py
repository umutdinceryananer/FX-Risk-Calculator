"""CLI command for seeding demo portfolio data."""

from __future__ import annotations

import click
from flask.cli import with_appcontext

from app.services.demo_seed import seed_demo_portfolio


@click.command("seed-demo")
@with_appcontext
def seed_demo() -> None:
    """Seed the Global Book demo portfolio with deterministic positions."""

    result = seed_demo_portfolio()
    portfolio_label = "Created" if result.created else "Updated"
    click.echo(
        f"{portfolio_label} '{'Global Book (USD)'}' with {result.positions_created} positions "
        f"(portfolio_id={result.portfolio_id})."
    )
