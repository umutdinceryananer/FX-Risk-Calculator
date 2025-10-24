"""Shared pytest fixtures."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

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
    flask_app.config["SCHEDULER_ENABLED"] = False

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


@pytest.fixture()
def db_session(app) -> Iterator:
    """Provide a database session that rolls back between tests."""

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        SessionLocal.remove()


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Return the path to bundled JSON fixtures."""

    return ROOT_DIR / "tests" / "fixtures"


@pytest.fixture()
def load_json_fixture(fixtures_dir: Path) -> Callable[[str], dict]:
    """Load a JSON fixture by filename."""

    def _loader(filename: str) -> dict:
        path = fixtures_dir / filename
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    return _loader
