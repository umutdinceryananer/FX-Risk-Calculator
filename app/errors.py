"""Application-wide error utilities and handlers."""

from __future__ import annotations

from typing import Any, Dict

from flask import Flask, jsonify


class APIError(Exception):
    """Base class for API-level errors."""

    status_code: int = 400

    def __init__(self, message: str, *, status_code: int | None = None, payload: Dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}


class ValidationError(APIError):
    """Error raised for validation failures."""

    status_code = 422


DEFAULT_STATUS_MESSAGES: Dict[int, str] = {
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
        response = {"message": message}
        if error.payload:
            response.update(error.payload)
        return jsonify(response), error.status_code
