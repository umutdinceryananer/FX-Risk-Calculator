"""Route handlers for health checks."""

from __future__ import annotations

from flask import Response, current_app, jsonify

from . import bp


@bp.get("")
@bp.get("/")
def health() -> Response:
    """Return a basic readiness response for the service."""

    payload = {
        "status": "ok",
        "app": current_app.config.get("APP_NAME", "fx-risk-calculator"),
    }
    return jsonify(payload)


@bp.get("/rates")
def health_rates() -> Response:
    """Return the status of FX rates fetching components (stub)."""

    payload = {
        "status": "ok",
        "rates_status": "uninitialized",
    }
    return jsonify(payload)
