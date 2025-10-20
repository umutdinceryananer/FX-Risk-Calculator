"""Application configuration classes."""

from __future__ import annotations

import os
from typing import Type


class BaseConfig:
    """Base configuration shared across environments."""
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    RATES_REFRESH_CRON = os.getenv("RATES_REFRESH_CRON", "0 */1 * * *")

    APP_NAME = "fx-risk-calculator"
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///fx-risk-calculator.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "UTC")
    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
    FX_RATE_PROVIDER = os.getenv("FX_RATE_PROVIDER", "mock")
    RATES_API_BASE_URL = os.getenv("RATES_API_BASE_URL", "https://api.exchangerate.host")
    RATES_API_MAX_RETRIES = int(os.getenv("RATES_API_MAX_RETRIES", "3"))
    RATES_API_BACKOFF_SECONDS = float(os.getenv("RATES_API_BACKOFF_SECONDS", "0.5"))
    FRANKFURTER_API_BASE_URL = os.getenv("FRANKFURTER_API_BASE_URL", "https://api.frankfurter.app")
    FRANKFURTER_API_MAX_RETRIES = int(os.getenv("FRANKFURTER_API_MAX_RETRIES", "3"))
    FRANKFURTER_API_BACKOFF_SECONDS = float(os.getenv("FRANKFURTER_API_BACKOFF_SECONDS", "0.5"))
    FX_FALLBACK_PROVIDER = os.getenv("FX_FALLBACK_PROVIDER")
    FX_CANONICAL_BASE = os.getenv("FX_CANONICAL_BASE", "USD")
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    CORS_ALLOWED_HEADERS = os.getenv("CORS_ALLOWED_HEADERS", "Content-Type,Authorization")
    CORS_ALLOWED_METHODS = os.getenv("CORS_ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
    CORS_MAX_AGE = int(os.getenv("CORS_MAX_AGE", "600"))


class DevelopmentConfig(BaseConfig):
    """Configuration for local development."""

    DEBUG = True
    TESTING = False


class ProductionConfig(BaseConfig):
    """Configuration for production deployments."""

    DEBUG = False
    TESTING = False


CONFIG_BY_ENV = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config(config_name: str | None = None) -> Type[BaseConfig]:
    """Return the config class for the requested environment.

    Args:
        config_name: Optional explicit config identifier. If omitted, the
            APP_ENV environment variable is consulted.

    Raises:
        KeyError: If the requested configuration is not defined.
    """

    env_name = (config_name or os.getenv("APP_ENV", "development")).lower()
    try:
        return CONFIG_BY_ENV[env_name]
    except KeyError as exc:
        raise KeyError(f"Unknown APP_ENV '{env_name}'") from exc
