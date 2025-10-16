"""Routes for currency validation."""

from __future__ import annotations

from flask.views import MethodView

from app.schemas import (
    CurrencyValidationRequestSchema,
    CurrencyValidationResponseSchema,
)
from app.validation import validate_currency_code

from . import blp


@blp.route("/validate")
class CurrencyValidation(MethodView):
    @blp.arguments(CurrencyValidationRequestSchema)
    @blp.response(200, CurrencyValidationResponseSchema())
    def post(self, data):
        validated = validate_currency_code(data.get("code"), field="code")
        return {
            "code": validated,
            "message": "Currency code is valid.",
        }
