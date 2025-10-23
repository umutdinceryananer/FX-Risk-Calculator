"""Lightweight helpers for capturing operation timing metrics."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from time import perf_counter
from typing import Any, Mapping, MutableMapping, Optional

from flask import current_app, g

LOG_EVENT_NAME = "performance.timing"
CONFIG_ENABLED_KEY = "TIMING_LOGS_ENABLED"
CONFIG_THRESHOLD_KEY = "TIMING_MIN_DURATION_MS"


def _is_enabled(app) -> bool:
    value = app.config.get(CONFIG_ENABLED_KEY, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _threshold_ms(app) -> Optional[float]:
    value = app.config.get(CONFIG_THRESHOLD_KEY)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _current_request_id() -> Optional[str]:
    return getattr(g, "request_id", None)


def _should_log(duration_ms: float, *, enabled: bool, threshold_ms: Optional[float]) -> bool:
    if enabled:
        return True
    if threshold_ms is None:
        return False
    return duration_ms >= threshold_ms


def _prepare_payload(
    *,
    event: str,
    duration_ms: float,
    metadata: Optional[Mapping[str, Any]],
    status: str,
    error: Optional[str] = None,
) -> MutableMapping[str, Any]:
    payload: MutableMapping[str, Any] = {
        "event": event or LOG_EVENT_NAME,
        "duration_ms": round(duration_ms, 3),
        "source": "performance",
        "status": status,
    }
    request_id = _current_request_id()
    if request_id:
        payload["request_id"] = request_id

    if metadata:
        for key, value in metadata.items():
            payload[str(key)] = value
    if error:
        payload["error"] = error
    return payload


@contextmanager
def timed_operation(
    event: str,
    *,
    metadata: Optional[Mapping[str, Any]] = None,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Measure the elapsed wall time for a block and log if enabled."""

    app = current_app._get_current_object()
    enabled = _is_enabled(app)
    threshold_ms = _threshold_ms(app)

    logger = logger or app.logger
    start = perf_counter()
    error: Optional[Exception] = None
    try:
        yield
    except Exception as exc:
        error = exc
        raise
    finally:
        duration_ms = (perf_counter() - start) * 1000
        if _should_log(duration_ms, enabled=enabled, threshold_ms=threshold_ms):
            status = "error" if error else "success"
            payload = _prepare_payload(
                event=event,
                duration_ms=duration_ms,
                metadata=metadata,
                status=status,
                error=str(error) if error else None,
            )

            if error:
                logger.warning("Timing captured (error)", extra=payload)
            else:
                logger.info("Timing captured", extra=payload)


def timed(event: str, *, metadata_factory=None):
    """Decorator variant of ``timed_operation`` for function instrumentation."""

    def _decorator(func):
        def _wrapper(*args, **kwargs):
            metadata = metadata_factory(*args, **kwargs) if callable(metadata_factory) else None
            with timed_operation(event, metadata=metadata):
                return func(*args, **kwargs)

        return _wrapper

    return _decorator
