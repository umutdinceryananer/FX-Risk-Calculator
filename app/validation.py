"""Validation helpers for request payloads."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.errors import ValidationError
from app.services.currency_registry import registry


def _preview_codes(codes: Sequence[str], max_items: int = 10) -> str:
    subset = list(sorted(codes))[:max_items]
    preview = ", ".join(subset)
    if len(codes) > max_items:
        preview += ", ..."
    return preview


def validate_currency_code(value: str | None, *, field: str = "currency_code") -> str:
    """Ensure the provided currency code exists in the registry."""

    if value is None or not str(value).strip():
        raise ValidationError(f"'{field}' is required.", payload={"field": field})

    normalized = str(value).strip().upper()
    if not normalized.isascii():
        raise ValidationError(
            f"Unsupported currency code '{normalized}'. Please use a valid ISO 4217 code.",
            payload={"field": field, "code": normalized},
        )

    if not registry.is_allowed(normalized):
        codes: Iterable[str] = registry.codes
        hint = _preview_codes(tuple(codes)) if codes else "no codes configured"
        raise ValidationError(
            f"Unsupported currency code '{normalized}'. Allowed codes: {hint}.",
            payload={"field": field, "code": normalized},
        )

    return normalized
