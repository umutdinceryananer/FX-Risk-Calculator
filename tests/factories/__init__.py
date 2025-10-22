"""Helper factories for building common payloads and domain objects in tests."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def make_portfolio_payload(
    name: str = "Global Book",
    base_currency: str = "USD",
) -> dict[str, Any]:
    """Return a portfolio creation payload."""

    return {"name": name, "base_currency": base_currency}


def make_position_payload(
    currency_code: str = "EUR",
    amount: Decimal | str = Decimal("1000"),
    side: str = "LONG",
) -> dict[str, Any]:
    """Return a position creation payload."""

    amount_str = str(amount) if isinstance(amount, Decimal) else amount
    return {"currency_code": currency_code, "amount": amount_str, "side": side}


def make_rate_quote(
    base_currency: str = "USD",
    quote_currency: str = "EUR",
    rate: Decimal = Decimal("0.92"),
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Return a normalized FX quote dictionary."""

    timestamp = as_of or datetime.now(UTC)
    return {
        "base_currency": base_currency,
        "quote_currency": quote_currency,
        "rate": str(rate),
        "as_of": timestamp.isoformat(),
    }


@dataclass(slots=True)
class SnapshotFixture:
    """Container simplifying construction of snapshot payloads for metrics tests."""

    base_currency: str
    rates: Mapping[str, Decimal]
    as_of: datetime

    def to_payload(self) -> dict[str, Any]:
        """Render snapshot details into a payload-friendly structure."""

        return {
            "base_currency": self.base_currency,
            "rates": {code: str(value) for code, value in self.rates.items()},
            "as_of": self.as_of.isoformat(),
        }


def make_snapshot(
    base_currency: str,
    rates: Mapping[str, Decimal] | Iterable[tuple[str, Decimal]],
    as_of: datetime | None = None,
) -> SnapshotFixture:
    """Return a snapshot fixture with uniform formatting."""

    if not isinstance(rates, Mapping):
        rates = dict(rates)
    timestamp = as_of or datetime.now(UTC)
    return SnapshotFixture(base_currency=base_currency, rates=rates, as_of=timestamp)
