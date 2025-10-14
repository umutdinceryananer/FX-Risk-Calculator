"""SQLAlchemy database helpers and session management."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# Thread-local scoped session used across the application.
SessionLocal = scoped_session(sessionmaker())

_engine: Optional[Engine] = None


def init_app(app: Any) -> None:
    """Configure SQLAlchemy engine and session for the Flask application."""

    global _engine

    if _engine is not None:
        return

    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    _engine = create_engine(database_uri, future=True)
    SessionLocal.configure(bind=_engine, autoflush=False)

    @app.teardown_appcontext
    def shutdown_session(_: Optional[BaseException] = None) -> None:
        SessionLocal.remove()

    app.extensions["sqlalchemy_engine"] = _engine
    app.extensions["sqlalchemy_session_factory"] = SessionLocal


def get_engine() -> Engine:
    """Return the active SQLAlchemy engine; raise if not yet initialized."""

    if _engine is None:
        raise RuntimeError("Database engine has not been initialized. Call init_app first.")
    return _engine


def get_session() -> scoped_session:
    """Expose the configured session factory."""

    return SessionLocal
