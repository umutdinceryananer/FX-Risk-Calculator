"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app


@pytest.fixture(scope="session")
def app():
    """Session-wide Flask application for tests."""

    app = create_app("development")
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def client(app):
    """Provide a Flask test client."""

    with app.test_client() as client:
        yield client
