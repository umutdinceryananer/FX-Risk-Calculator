"""Logging helpers and structured JSON formatter for the FX Risk Calculator."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from flask import g, has_request_context, request
from werkzeug.exceptions import HTTPException

REQUEST_ID_HEADER = "X-Request-ID"

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
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
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

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(level)
    werkzeug_logger.handlers = []
    app.logger.handlers = []
    app.logger.setLevel(level)
    app.logger.propagate = True

    app.config[LOGGING_CONFIG_FLAG] = True


def init_request_logging(app) -> None:
    """Attach request lifecycle logging with correlation IDs."""

    if app.config.get("_request_logging_configured"):
        return

    @app.before_request
    def _start_request_logging():
        request_id = request.headers.get(REQUEST_ID_HEADER)
        if not request_id:
            request_id = uuid.uuid4().hex
        g.request_id = request_id
        g.request_start = time.perf_counter()
        g._request_logged = False

    @app.after_request
    def _log_request(response):
        request_id = getattr(g, "request_id", None)
        if request_id:
            response.headers.setdefault(REQUEST_ID_HEADER, request_id)

        duration_ms = _request_duration_ms()
        extras = _build_request_log_extra(
            event="request.completed",
            status=response.status_code,
            request_id=request_id,
            duration_ms=duration_ms,
            error=None,
        )
        app.logger.info("Request handled", extra=extras)
        g._request_logged = True
        return response

    @app.teardown_request
    def _log_teardown(exc: BaseException | None):
        if exc is None:
            return
        if getattr(g, "_request_logged", False):
            return

        request_id = getattr(g, "request_id", None)
        status = getattr(exc, "code", 500) if isinstance(exc, HTTPException) else 500
        duration_ms = _request_duration_ms()
        extras = _build_request_log_extra(
            event="request.failed",
            status=status,
            request_id=request_id,
            duration_ms=duration_ms,
            error=str(exc),
        )
        app.logger.error("Request failed", extra=extras)
        g._request_logged = True

    app.config["_request_logging_configured"] = True


def _request_duration_ms() -> float | None:
    start = getattr(g, "request_start", None)
    if not isinstance(start, int | float):
        return None
    return float((time.perf_counter() - start) * 1000)


def _build_request_log_extra(
    *,
    event: str,
    status: int,
    request_id: str | None,
    duration_ms: float | None,
    error: str | None,
) -> dict[str, Any]:
    route = request.url_rule.rule if request.url_rule else request.path
    payload: dict[str, Any] = {
        "event": event,
        "route": route,
        "method": request.method,
        "status": status,
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "request_id": request_id,
        "path": request.path,
        "source": "api",
        "stale": False,
    }
    if error:
        payload["error"] = error
    if request.remote_addr:
        payload["client_ip"] = request.remote_addr

    return {key: value for key, value in payload.items() if value is not None}


def _extract_extras(record_dict: dict[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for key, value in record_dict.items():
        if key in RESERVED_ATTRS or key.startswith("_"):
            continue
        extras[key] = _json_safe(value)
    return extras


def _json_safe(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
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


def provider_log_extra(
    *,
    provider: str,
    base: str,
    event: str,
    status: str,
    duration_ms: float | None,
    stale: bool,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "event": event,
        "provider": provider,
        "base": base,
        "status": status,
        "duration_ms": round(duration_ms, 3) if duration_ms is not None else None,
        "request_id": _current_request_id(),
        "source": provider,
        "stale": stale,
    }
    if error:
        payload["error"] = error
    return {key: value for key, value in payload.items() if value is not None}


def _current_request_id() -> str | None:
    if not has_request_context():
        return None
    return getattr(g, "request_id", None)
