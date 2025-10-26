"""Application configuration classes."""

from __future__ import annotations

import os

SUPPORTED_RATE_PROVIDERS = {"exchange", "exchangerate_host", "ecb", "frankfurter_ecb", "mock"}
PROVIDER_ALIASES = {"exchangerate_host": "exchange", "frankfurter_ecb": "ecb"}


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
    FX_RATE_PROVIDER = os.getenv("FX_RATE_PROVIDER", "exchange")
    RATES_API_BASE_URL = os.getenv("RATES_API_BASE_URL", "https://api.exchangerate.host")
    RATES_API_MAX_RETRIES = int(os.getenv("RATES_API_MAX_RETRIES", "3"))
    RATES_API_BACKOFF_SECONDS = float(os.getenv("RATES_API_BACKOFF_SECONDS", "0.5"))
    FRANKFURTER_API_BASE_URL = os.getenv("FRANKFURTER_API_BASE_URL", "https://api.frankfurter.app")
    FRANKFURTER_API_MAX_RETRIES = int(os.getenv("FRANKFURTER_API_MAX_RETRIES", "3"))
    FRANKFURTER_API_BACKOFF_SECONDS = float(os.getenv("FRANKFURTER_API_BACKOFF_SECONDS", "0.5"))
    FX_FALLBACK_PROVIDER = os.getenv("FX_FALLBACK_PROVIDER", "ecb")
    FX_CANONICAL_BASE = os.getenv("FX_CANONICAL_BASE", "USD")
    REFRESH_THROTTLE_SECONDS = int(os.getenv("REFRESH_THROTTLE_SECONDS", "60"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_JSON_ENABLED = os.getenv("LOG_JSON_ENABLED", "false").lower() == "true"
    LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s %(levelname)s [%(name)s] %(message)s")
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


def get_config(config_name: str | None = None) -> type[BaseConfig]:
    """Return the config class for the requested environment.

    Args:
        config_name: Optional explicit config identifier. If omitted, the
            APP_ENV environment variable is consulted.

    Raises:
        KeyError: If the requested configuration is not defined.
    """

    env_name = (config_name or os.getenv("APP_ENV", "development")).lower()
    try:
        config_cls = CONFIG_BY_ENV[env_name]
    except KeyError as exc:
        raise KeyError(f"Unknown APP_ENV '{env_name}'") from exc

    _validate_providers(config_cls)
    return config_cls


def _validate_providers(config_cls: type[BaseConfig]) -> None:
    primary_normalized = _normalize_provider(config_cls.FX_RATE_PROVIDER)
    if primary_normalized not in SUPPORTED_RATE_PROVIDERS:
        raise ValueError(
            f"Unsupported FX_RATE_PROVIDER '{config_cls.FX_RATE_PROVIDER}'. "
            f"Allowed values: {sorted(SUPPORTED_RATE_PROVIDERS)}"
        )
    config_cls.FX_RATE_PROVIDER = primary_normalized

    fallback_raw = config_cls.FX_FALLBACK_PROVIDER
    if fallback_raw:
        fallback_normalized = _normalize_provider(fallback_raw)
        if fallback_normalized not in SUPPORTED_RATE_PROVIDERS:
            raise ValueError(
                f"Unsupported FX_FALLBACK_PROVIDER '{fallback_raw}'. Allowed values: "
                f"{sorted(SUPPORTED_RATE_PROVIDERS)}"
            )
        config_cls.FX_FALLBACK_PROVIDER = fallback_normalized
    else:
        config_cls.FX_FALLBACK_PROVIDER = None


def _normalize_provider(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.lower()
    return PROVIDER_ALIASES.get(normalized, normalized)
