"""CLI entry points."""

from __future__ import annotations

from flask import Flask

from .backfill import backfill_rates


def register_cli(app: Flask) -> None:
    """Register CLI commands on the given Flask app."""

    app.cli.add_command(backfill_rates)
