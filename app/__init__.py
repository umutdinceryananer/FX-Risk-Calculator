"""Application factory for the FX Risk Calculator service."""

from __future__ import annotations

from flask import Flask
from flask_smorest import Api

from config import get_config
from .database import init_app as init_db
from .cli import register_cli


def create_app(config_name: str | None = None) -> Flask:
    """Application factory adhering to the Flask app factory pattern."""

    app = Flask(__name__)
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    _configure_api(app)
    _register_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)

    register_cli(app)
    return app


def _configure_api(app: Flask) -> None:
    app.config.setdefault("API_TITLE", "FX Risk Calculator API")
    app.config.setdefault("API_VERSION", "v1")
    app.config.setdefault("OPENAPI_VERSION", "3.0.3")
    app.config.setdefault("OPENAPI_URL_PREFIX", "/docs")
    app.config.setdefault("OPENAPI_SWAGGER_UI_PATH", "/")
    app.config.setdefault(
        "OPENAPI_SWAGGER_UI_URL",
        "https://cdn.jsdelivr.net/npm/swagger-ui-dist/",
    )


def _register_extensions(app: Flask) -> None:
    """Placeholder for initializing extensions (SQLAlchemy, APScheduler, etc.)."""

    init_db(app)
    from . import models  # noqa: F401  # Ensure models are imported for metadata
    from .services import ensure_refresh_state, init_registry, init_orchestrator, init_scheduler
    from .providers.registry import init_provider

    init_registry(app)
    init_provider(app)
    init_orchestrator(app)
    ensure_refresh_state(app)
    init_scheduler(app)

    api = Api(app)
    app.extensions["smorest_api"] = api


def _register_blueprints(app: Flask) -> None:
    """Register Flask blueprints."""

    from .health import bp as health_bp
    from .currencies import bp as currencies_bp
    from .rates import bp as rates_bp

    app.register_blueprint(health_bp, url_prefix="/health")
    app.register_blueprint(currencies_bp, url_prefix="/currencies")
    app.register_blueprint(rates_bp, url_prefix="/rates")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    from .errors import register_error_handlers

    register_error_handlers(app)
