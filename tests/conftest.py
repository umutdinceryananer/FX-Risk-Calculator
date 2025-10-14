"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterator

import pytest
from alembic import command
from alembic.config import Config

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app  # noqa: E402
from app.database import SessionLocal, get_engine  # noqa: E402
from app.services.currency_registry import registry  # noqa: E402


@pytest.fixture(scope="session")
def app(tmp_path_factory: pytest.TempPathFactory) -> Iterator:
    """Session-wide Flask application configured with a temporary database."""

    db_dir = tmp_path_factory.mktemp("db")
    db_path = db_dir / "test.db"
    database_url = f"sqlite:///{db_path}"

    previous_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url

    alembic_cfg = Config(str(ROOT_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")

    flask_app = create_app("development")
    flask_app.config.update(TESTING=True)

    yield flask_app

    engine = get_engine()
    SessionLocal.remove()
    engine.dispose()
    command.downgrade(alembic_cfg, "base")
    registry.codes.clear()

    if previous_db_url is not None:
        os.environ["DATABASE_URL"] = previous_db_url
    else:
        os.environ.pop("DATABASE_URL", None)


@pytest.fixture()
def client(app):
    """Provide a Flask test client."""

    with app.test_client() as client:
        yield client
