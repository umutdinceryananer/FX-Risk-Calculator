from __future__ import annotations

import json
import logging
from contextlib import contextmanager

import pytest
from flask import Flask

from app.logging import JSONLogFormatter, init_request_logging, setup_logging


class _MemoryHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@contextmanager
def isolate_logging():
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    try:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        yield root
    finally:
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        for handler in previous_handlers:
            root.addHandler(handler)
        root.setLevel(previous_level)


def test_json_log_formatter_renders_basic_fields():
    formatter = JSONLogFormatter()
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="Hello %s",
        args=("world",),
        exc_info=None,
    )
    record.request_id = "req-123"

    payload = json.loads(formatter.format(record))

    assert payload["message"] == "Hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert "timestamp" in payload
    assert payload["request_id"] == "req-123"


def test_setup_logging_enables_json_formatter_when_configured():
    app = Flask(__name__)
    app.config["LOG_JSON_ENABLED"] = True
    app.config["LOG_LEVEL"] = "DEBUG"

    with isolate_logging():
        setup_logging(app)
        root = logging.getLogger()
        assert root.level == logging.DEBUG
        assert app.logger.level == logging.DEBUG
        assert root.handlers, "Expected handler to be registered on root logger"
        handler = root.handlers[0]
        assert isinstance(handler.formatter, JSONLogFormatter)


def test_setup_logging_uses_plain_formatter_by_default():
    app = Flask(__name__)
    app.config["LOG_JSON_ENABLED"] = False
    app.config["LOG_LEVEL"] = "WARNING"
    app.config["LOG_FORMAT"] = "%(levelname)s:%(message)s"

    with isolate_logging():
        setup_logging(app)
        root = logging.getLogger()
        assert root.level == logging.WARNING
        handler = root.handlers[0]
        assert isinstance(handler.formatter, logging.Formatter)
        assert handler.formatter._style._fmt == "%(levelname)s:%(message)s"


def _make_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/ok")
    def ok():  # pragma: no cover - invoked via test client
        return "ok", 200

    @app.route("/boom")
    def boom():  # pragma: no cover - invoked via test client
        raise RuntimeError("boom")

    return app


def test_request_logging_emits_correlation_fields():
    app = _make_test_app()
    app.config["LOG_JSON_ENABLED"] = False

    with isolate_logging():
        setup_logging(app)
        init_request_logging(app)
        handler = _MemoryHandler()
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        client = app.test_client()
        response = client.get("/ok")

    records = [record for record in handler.records if record.message == "Request handled"]
    assert records
    record = records[-1]
    assert record.event == "request.completed"
    assert record.method == "GET"
    assert record.status == 200
    assert record.request_id == response.headers["X-Request-ID"]
    assert record.source == "api"
    assert record.stale is False
    assert record.duration_ms is not None and record.duration_ms >= 0
    assert record.route in {"/ok", "ok"}


def test_request_logging_captures_errors():
    app = _make_test_app()

    with isolate_logging():
        setup_logging(app)
        init_request_logging(app)
        handler = _MemoryHandler()
        handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(handler)
        client = app.test_client()
        with pytest.raises(RuntimeError):
            client.get("/boom")

    records = [record for record in handler.records if record.message == "Request failed"]
    assert records
    record = records[-1]
    assert record.event == "request.failed"
    assert record.status == 500
    assert record.request_id
    assert record.duration_ms is not None and record.duration_ms >= 0
    assert "boom" in record.error
