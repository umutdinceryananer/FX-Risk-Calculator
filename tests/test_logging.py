from __future__ import annotations

import json
import logging
from contextlib import contextmanager

from flask import Flask

from app.logging import JSONLogFormatter, setup_logging


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
