"""CLI entry points."""

from __future__ import annotations

from flask import Flask

from .backfill import backfill_rates
from .seed_demo import seed_demo


def register_cli(app: Flask) -> None:
    """Register CLI commands on the given Flask app."""

    app.cli.add_command(backfill_rates)
    app.cli.add_command(seed_demo)
