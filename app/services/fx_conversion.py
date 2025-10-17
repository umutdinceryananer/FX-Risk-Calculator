"""Shared utilities for FX rate conversions and snapshot rebasing."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, getcontext, localcontext
from typing import Dict, Mapping, MutableMapping


ROUNDING_PRECISION = 28


def get_decimal_context():
    """Return the shared Decimal context used across FX conversions."""

    context = getcontext().copy()
    context.prec = ROUNDING_PRECISION
    context.rounding = ROUND_HALF_EVEN
    return context


def normalize_currency(code: str) -> str:
    """Normalize a currency code to canonical uppercase form."""

    if not code or not str(code).strip():
        raise ValueError("Currency code cannot be blank.")
    normalized = str(code).strip().upper()
    if not normalized.isascii():
        raise ValueError(f"Currency code must be ASCII: {code!r}")
    return normalized


def to_decimal(value: Decimal | int | float | str) -> Decimal:
    """Convert input into a Decimal using the shared context."""

    context = get_decimal_context()
    with localcontext(context):
        return Decimal(str(value))


class RebaseError(ValueError):
    """Raised when rebasing rates fails due to missing data."""


def rebase_rates(rates: Mapping[str, Decimal], new_base: str) -> Dict[str, Decimal]:
    """Rebase a mapping of rates (expressed against a canonical base) to a new base."""

    normalized_rates: MutableMapping[str, Decimal] = {}
    for code, value in rates.items():
        normalized_rates[normalize_currency(code)] = to_decimal(value)

    target_base = normalize_currency(new_base)

    if target_base not in normalized_rates:
        raise RebaseError(f"Missing rate for {target_base} when rebasing snapshot.")

    base_rate = normalized_rates[target_base]
    if base_rate == 0:
        raise RebaseError(f"Cannot rebase using {target_base} with zero rate.")

    context = get_decimal_context()
    with localcontext(context):
        rebased: Dict[str, Decimal] = {}
        for code, value in normalized_rates.items():
            rebased[code] = value / base_rate

    return rebased


def convert_amount(
    amount: Decimal | int | float | str,
    rate: Decimal | int | float | str,
    *,
    side: str = "LONG",
) -> Decimal:
    """Convert a native amount into base using the provided rate and position side."""

    raise NotImplementedError("Conversion logic will be implemented in a subsequent commit.")


def convert_position_amount(
    *,
    native_amount: Decimal,
    position_currency: str,
    portfolio_base: str,
    rate_lookup: Mapping[str, Decimal],
    side: str,
) -> Decimal:
    """Convert a position's native amount into the portfolio base currency."""

    raise NotImplementedError("Conversion logic will be implemented in a subsequent commit.")


def rebase_snapshot(rates_usd: Mapping[str, Decimal], new_base: str) -> Dict[str, Decimal]:
    """Rebase a canonical USD snapshot into another base currency."""

    raise NotImplementedError("Snapshot rebasing will be implemented in a subsequent commit.")
