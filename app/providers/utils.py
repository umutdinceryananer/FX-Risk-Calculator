"""Helper utilities for provider rate transformations."""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Mapping


class RebaseError(ValueError):
    """Raised when rebasing rates fails due to missing data."""


def rebase_rates(rates: Mapping[str, Decimal], new_base: str) -> Dict[str, Decimal]:
    """Rebase a mapping of rates (expressed against a canonical base) to a new base.

    Args:
        rates: Mapping of currency codes to Decimal exchange rates relative to a
            canonical base (e.g., USD). The mapping must include the desired
            `new_base` currency and the canonical base (with value 1).
        new_base: ISO code to rebase to.

    Returns:
        A dictionary of rebased rates including the new base with value 1.

    Raises:
        RebaseError: If the requested base is missing or has a zero rate.
    """

    normalized_rates = {code.upper(): Decimal(rate) for code, rate in rates.items()}
    normalized_new_base = new_base.strip().upper()

    if normalized_new_base not in normalized_rates:
        raise RebaseError(f"Missing rate for {normalized_new_base} when rebasing snapshot.")

    base_rate = normalized_rates[normalized_new_base]
    if base_rate == 0:
        raise RebaseError(f"Cannot rebase using {normalized_new_base} with zero rate.")

    rebased: Dict[str, Decimal] = {}
    for code, value in normalized_rates.items():
        rebased[code] = value / base_rate

    return rebased
