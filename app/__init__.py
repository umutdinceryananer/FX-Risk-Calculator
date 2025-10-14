"""Application factory for the FX Risk Calculator service."""

from __future__ import annotations

from flask import Flask

from config import get_config
from .database import init_app as init_db


def create_app(config_name: str | None = None) -> Flask:
    """Application factory adhering to the Flask app factory pattern."""

    app = Flask(__name__)
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    _register_extensions(app)
    _register_blueprints(app)

    return app


def _register_extensions(app: Flask) -> None:
    """Placeholder for initializing extensions (SQLAlchemy, APScheduler, etc.)."""

    init_db(app)
    from . import models  # noqa: F401  # Ensure models are imported for metadata


def _register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""

    from .health import bp as health_bp

    app.register_blueprint(health_bp, url_prefix="/health")
