"""Lightweight CORS helpers for the FX Risk Calculator API."""

from __future__ import annotations

from collections.abc import Iterable

from flask import Response, make_response, request


def init_cors(app) -> None:
    """Configure simple CORS handling based on application settings."""

    if app.config.get("_cors_configured"):
        return

    allowed_origins = _normalize_entries(app.config.get("CORS_ALLOWED_ORIGINS", ()))
    if not allowed_origins:
        return

    allowed_headers = _normalize_entries(
        app.config.get("CORS_ALLOWED_HEADERS", ("Content-Type", "Authorization"))
    )
    allowed_methods = _normalize_entries(
        app.config.get(
            "CORS_ALLOWED_METHODS",
            ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
        )
    )
    max_age = int(app.config.get("CORS_MAX_AGE", 600))

    def origin_allowed(origin: str | None) -> bool:
        if not origin:
            return False
        if "*" in allowed_origins:
            return True
        return origin in allowed_origins

    @app.before_request
    def handle_preflight():
        if request.method != "OPTIONS":
            return None

        origin = request.headers.get("Origin")
        if origin is None:
            return None
        if not origin_allowed(origin):
            return make_response("", 403)

        response = make_response("", 204)
        _apply_origin_headers(response, origin, allowed_origins)
        response.headers["Access-Control-Allow-Methods"] = ", ".join(
            _requested_methods(allowed_methods)
        )
        response.headers["Access-Control-Allow-Headers"] = request.headers.get(
            "Access-Control-Request-Headers",
            ", ".join(allowed_headers),
        )
        response.headers["Access-Control-Max-Age"] = str(max_age)
        return response

    @app.after_request
    def apply_cors(response: Response):
        origin = request.headers.get("Origin")
        if origin and origin_allowed(origin):
            _apply_origin_headers(response, origin, allowed_origins)
        return response

    app.config["_cors_configured"] = True


def _normalize_entries(raw: str | Iterable[str]) -> tuple[str, ...]:
    if isinstance(raw, str):
        candidates = raw.split(",")
    else:
        candidates = list(raw)
    normalized: list[str] = []
    for value in candidates:
        item = (value or "").strip()
        if item:
            normalized.append(item)
    return tuple(normalized)


def _apply_origin_headers(
    response: Response,
    origin: str,
    allowed_origins: tuple[str, ...],
) -> None:
    response.headers["Access-Control-Allow-Origin"] = origin if "*" not in allowed_origins else "*"
    response.headers["Vary"] = _merge_vary_header(response.headers.get("Vary"), "Origin")


def _merge_vary_header(existing: str | None, value: str) -> str:
    if not existing:
        return value
    items = [item.strip() for item in existing.split(",") if item.strip()]
    if value not in items:
        items.append(value)
    return ", ".join(items)


def _requested_methods(default_methods: tuple[str, ...]) -> tuple[str, ...]:
    requested = request.headers.get("Access-Control-Request-Method")
    if not requested:
        return default_methods
    if requested in default_methods:
        return default_methods
    return default_methods + (requested,)
