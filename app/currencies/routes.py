"""Routes for currency validation."""

from __future__ import annotations

from flask import jsonify, request

from app.validation import validate_currency_code

from . import bp


@bp.post("/validate")
def validate_currency():
    """Validate a currency code against the configured allowlist."""

    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    validated = validate_currency_code(code, field="code")

    return jsonify(
        {
            "code": validated,
            "message": "Currency code is valid.",
        }
    )
