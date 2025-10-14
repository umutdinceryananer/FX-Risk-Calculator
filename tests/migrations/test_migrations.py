"""Smoke tests for Alembic migrations."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = PROJECT_ROOT / "alembic.ini"


@pytest.fixture()
def alembic_config(tmp_path):
    """Provide an Alembic config pointing to a temporary SQLite database."""

    # Copy the base config so we can override the database URL per test.
    config = Config(str(ALEMBIC_CONFIG_PATH))
    db_path = tmp_path / "test.db"
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def _table_exists(engine, table_name: str) -> bool:
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=:table_name"
                ),
                {"table_name": table_name},
            )
            return result.first() is not None
    except OperationalError:
        return False


def test_alembic_upgrade_and_downgrade(alembic_config, tmp_path):
    """Ensure migrations upgrade and downgrade cleanly on a blank database."""

    command.upgrade(alembic_config, "head")

    engine = create_engine(alembic_config.get_main_option("sqlalchemy.url"))
    assert _table_exists(engine, "currencies")
    assert _table_exists(engine, "portfolios")
    assert _table_exists(engine, "fx_rates")
    assert _table_exists(engine, "positions")

    command.downgrade(alembic_config, "base")

    assert not _table_exists(engine, "currencies")
    assert not _table_exists(engine, "portfolios")
    assert not _table_exists(engine, "fx_rates")
    assert not _table_exists(engine, "positions")
