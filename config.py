"""Application configuration classes."""

from __future__ import annotations

import os

SUPPORTED_RATE_PROVIDERS = {"exchange", "exchangerate_host", "ecb", "frankfurter_ecb", "mock"}
PROVIDER_ALIASES = {"exchangerate_host": "exchange", "frankfurter_ecb": "ecb"}


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value is not None else default


class BaseConfig:
    """Base configuration shared across environments."""

    SCHEDULER_ENABLED = _get_env("SCHEDULER_ENABLED", "true").lower() == "true"
    RATES_REFRESH_CRON = _get_env("RATES_REFRESH_CRON", "0 */1 * * *")

    APP_NAME = "fx-risk-calculator"
    SECRET_KEY = _get_env("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = _get_env("DATABASE_URL", "sqlite:///fx-risk-calculator.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SCHEDULER_TIMEZONE = _get_env("SCHEDULER_TIMEZONE", "UTC")
    REQUEST_TIMEOUT_SECONDS = int(_get_env("REQUEST_TIMEOUT_SECONDS", "5"))
    FX_RATE_PROVIDER = _get_env("FX_RATE_PROVIDER", "exchange")
    RATES_API_BASE_URL = _get_env("RATES_API_BASE_URL", "https://api.exchangerate.host")
    RATES_API_MAX_RETRIES = int(_get_env("RATES_API_MAX_RETRIES", "3"))
    RATES_API_BACKOFF_SECONDS = float(_get_env("RATES_API_BACKOFF_SECONDS", "0.5"))
    FRANKFURTER_API_BASE_URL = _get_env("FRANKFURTER_API_BASE_URL", "https://api.frankfurter.app")
    FRANKFURTER_API_MAX_RETRIES = int(_get_env("FRANKFURTER_API_MAX_RETRIES", "3"))
    FRANKFURTER_API_BACKOFF_SECONDS = float(_get_env("FRANKFURTER_API_BACKOFF_SECONDS", "0.5"))
    FX_FALLBACK_PROVIDER: str | None = _get_env("FX_FALLBACK_PROVIDER", "ecb")
    FX_CANONICAL_BASE = _get_env("FX_CANONICAL_BASE", "USD")
    REFRESH_THROTTLE_SECONDS = int(_get_env("REFRESH_THROTTLE_SECONDS", "60"))
    LOG_LEVEL = _get_env("LOG_LEVEL", "INFO")
    LOG_JSON_ENABLED = _get_env("LOG_JSON_ENABLED", "false").lower() == "true"
    LOG_FORMAT = _get_env("LOG_FORMAT", "%(asctime)s %(levelname)s [%(name)s] %(message)s")
    CORS_ALLOWED_ORIGINS = _get_env("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    CORS_ALLOWED_HEADERS = _get_env("CORS_ALLOWED_HEADERS", "Content-Type,Authorization")
    CORS_ALLOWED_METHODS = _get_env("CORS_ALLOWED_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS")
    CORS_MAX_AGE = int(_get_env("CORS_MAX_AGE", "600"))


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

    env_candidate = config_name if config_name is not None else os.getenv("APP_ENV", "development")
    env_name = (env_candidate or "development").lower()
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
