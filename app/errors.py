"""Application-wide error utilities and handlers."""

from __future__ import annotations

from typing import Any

from flask import Flask, jsonify


class APIError(Exception):
    """Base class for API-level errors."""

    status_code: int = 400

    def __init__(
        self, message: str, *, status_code: int | None = None, payload: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}


class ValidationError(APIError):
    """Error raised for validation failures."""

    status_code = 422


DEFAULT_STATUS_MESSAGES: dict[int, str] = {
    400: "Request could not be processed.",
    404: "Resource not found.",
    422: "Submitted data is invalid.",
    429: "Too many requests. Please try again shortly.",
    502: "Upstream provider unavailable.",
    503: "Service temporarily unavailable. Please retry in a moment.",
}


def register_error_handlers(app: Flask) -> None:
    """Attach error handlers to the Flask application."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        message = error.message or DEFAULT_STATUS_MESSAGES.get(error.status_code, "Request failed.")
        payload = error.payload or {}

        response = {"message": message}
        if payload:
            response.update(payload)

        field_errors = _derive_field_errors(payload, default_message=message)
        if field_errors and "field_errors" not in response:
            response["field_errors"] = field_errors
        if field_errors and "errors" not in response:
            response["errors"] = {
                "json": {key: list(values) for key, values in field_errors.items()}
            }

        return jsonify(response), error.status_code


def _derive_field_errors(
    payload: dict[str, Any],
    *,
    default_message: str | None = None,
) -> dict[str, list[str]]:
    """Translate payload fields into a flat field_errors mapping."""

    if not payload:
        return {}

    if isinstance(payload.get("field_errors"), dict):
        result: dict[str, list[str]] = {}
        for field, messages in payload["field_errors"].items():
            normalized = _normalize_messages(messages)
            if normalized:
                result[str(field)] = normalized
        return result

    if isinstance(payload.get("errors"), dict):
        return _flatten_error_tree(payload["errors"])

    field = payload.get("field")
    if field and default_message:
        return {str(field): [default_message]}

    return {}


def _normalize_messages(messages: Any) -> list[str]:
    if isinstance(messages, list):
        normalized: list[str] = []
        for item in messages:
            if item is None:
                continue
            if isinstance(item, str):
                normalized.append(item)
            else:
                normalized.append(str(item))
        return normalized

    if messages is None:
        return []

    if isinstance(messages, str):
        return [messages]

    return [str(messages)]


def _flatten_error_tree(errors: dict[str, Any]) -> dict[str, list[str]]:
    collected: dict[tuple[str, ...], list[str]] = {}

    def visit(node: Any, path: tuple[str, ...]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                next_path = path + (str(key),)
                visit(value, next_path)
            return

        if isinstance(node, list):
            for item in node:
                visit(item, path)
            return

        if node is None:
            return

        message = node if isinstance(node, str) else str(node)
        if not path:
            key = ("non_field_errors",)
        else:
            key = path
        collected.setdefault(key, []).append(message)

    visit(errors, tuple())

    flattened: dict[str, list[str]] = {}
    for path, messages in collected.items():
        key_parts = list(path)
        if key_parts and key_parts[0] == "json":
            key_parts = key_parts[1:]
        key_str = ".".join(part for part in key_parts if part) or "non_field_errors"
        flattened.setdefault(key_str, []).extend(messages)

    return flattened
