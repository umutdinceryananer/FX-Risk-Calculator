"""Logging helpers and structured JSON formatter for the FX Risk Calculator."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Iterable

LOGGING_CONFIG_FLAG = "_logging_configured"

RESERVED_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


class JSONLogFormatter(logging.Formatter):
    """Format LogRecord instances into structured JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = record.stack_info

        extras = _extract_extras(record.__dict__)
        if extras:
            payload.update(extras)

        return json.dumps(_json_safe(payload), separators=(",", ":"))


def setup_logging(app) -> None:
    """Configure application logging handlers and formatters."""

    if app.config.get(LOGGING_CONFIG_FLAG):
        return

    level = _resolve_level(app.config.get("LOG_LEVEL", "INFO"))
    json_enabled = _to_bool(app.config.get("LOG_JSON_ENABLED", False))
    format_string = app.config.get(
        "LOG_FORMAT",
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    handler = logging.StreamHandler()
    handler.setLevel(level)
    if json_enabled:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(logging.Formatter(format_string))

    root_logger = logging.getLogger()
    _replace_handlers(root_logger, [handler])
    root_logger.setLevel(level)

    logging.getLogger("werkzeug").setLevel(level)
    app.logger.handlers = []
    app.logger.setLevel(level)
    app.logger.propagate = True

    app.config[LOGGING_CONFIG_FLAG] = True


def _extract_extras(record_dict: dict[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key, value in record_dict.items():
        if key in RESERVED_ATTRS or key.startswith("_"):
            continue
        extras[key] = _json_safe(value)
    return extras


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return str(value)


def _resolve_level(level_name: Any) -> int:
    if isinstance(level_name, int):
        return level_name
    if not level_name:
        return logging.INFO
    candidate = str(level_name).upper()
    return getattr(logging, candidate, logging.INFO)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _replace_handlers(logger: logging.Logger, handlers: Iterable[logging.Handler]) -> None:
    for existing in logger.handlers[:]:
        logger.removeHandler(existing)
    for handler in handlers:
        logger.addHandler(handler)
