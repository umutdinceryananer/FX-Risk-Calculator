"""Service helpers for calculating portfolio metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from typing import Dict, List, Optional

from flask import current_app
from sqlalchemy import desc

from app.database import get_session
from app.errors import APIError
from app.models import FxRate, Portfolio, Position
from app.services.fx_conversion import (
    RebaseError,
    convert_amount,
    convert_position_amount,
    get_decimal_context,
    normalize_currency,
    rebase_rates,
    to_decimal,
)
from app.validation import validate_currency_code


@dataclass(frozen=True)
class PortfolioValueResult:
    """Calculated portfolio value expressed in a target base currency."""

    portfolio_id: int
    portfolio_base: str
    view_base: str
    value: Decimal
    priced: int
    unpriced: int
    as_of: Optional[datetime]


def calculate_portfolio_value(portfolio_id: int, *, view_base: Optional[str] = None) -> PortfolioValueResult:
    """Compute aggregate portfolio value in the requested base currency."""

    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")

    positions = (
        session.query(Position)
        .filter(Position.portfolio_id == portfolio.id)
        .all()
    )

    if not positions:
        return PortfolioValueResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            value=Decimal("0"),
            priced=0,
            unpriced=0,
            as_of=None,
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    rates_map, as_of = _latest_rates(session, canonical_base)

    if as_of is None or not rates_map:
        return PortfolioValueResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            value=Decimal("0"),
            priced=0,
            unpriced=len(positions),
            as_of=None,
        )

    effective_rates = _rates_in_view_base(rates_map, canonical_base, resolved_view_base)

    priced = 0
    unpriced = 0
    total = Decimal("0")
    context = get_decimal_context()
    with localcontext(context):
        for position in positions:
            try:
                converted = convert_position_amount(
                    native_amount=position.amount,
                    position_currency=position.currency_code,
                    portfolio_base=resolved_view_base,
                    rate_lookup=effective_rates,
                    side=position.side.value,
                )
            except RebaseError:
                unpriced += 1
                continue

            priced += 1
            total += converted

    return PortfolioValueResult(
        portfolio_id=portfolio.id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        value=total,
        priced=priced,
        unpriced=unpriced,
        as_of=as_of,
    )


def _latest_rates(session, canonical_base: str) -> tuple[Dict[str, Decimal], Optional[datetime]]:
    latest_timestamp: Optional[datetime] = (
        session.query(FxRate.timestamp)
        .filter(FxRate.base_currency_code == canonical_base)
        .order_by(desc(FxRate.timestamp))
        .limit(1)
        .scalar()
    )

    if latest_timestamp is None:
        return {}, None

    rows = (
        session.query(FxRate)
        .filter(
            FxRate.base_currency_code == canonical_base,
            FxRate.timestamp == latest_timestamp,
        )
        .all()
    )

    normalized_base = normalize_currency(canonical_base)
    rates: Dict[str, Decimal] = {normalized_base: Decimal("1")}
    for row in rows:
        rates[normalize_currency(row.target_currency_code)] = row.rate

    return rates, latest_timestamp


def _rates_in_view_base(
    rates_map: Dict[str, Decimal],
    canonical_base: str,
    view_base: str,
) -> Dict[str, Decimal]:
    canonical_norm = normalize_currency(canonical_base)
    view_norm = normalize_currency(view_base)

    if view_norm == canonical_norm:
        source_rates = rates_map
    else:
        source_rates = rebase_rates(rates_map, view_norm)
        source_rates[view_norm] = Decimal("1")

    context = get_decimal_context()
    base_per_unit: Dict[str, Decimal] = {}
    with localcontext(context):
        for code, quote in source_rates.items():
            normalized_code = normalize_currency(code)
            if normalized_code == view_norm:
                base_per_unit[normalized_code] = Decimal("1")
                continue
            if quote == 0:
                continue
            rate_decimal = to_decimal(quote)
            if rate_decimal == 0:
                continue
            base_per_unit[normalized_code] = Decimal("1") / rate_decimal

    return base_per_unit


@dataclass(frozen=True)
class CurrencyExposure:
    currency_code: str
    net_native: Decimal
    base_equivalent: Decimal


@dataclass(frozen=True)
class PortfolioExposureResult:
    portfolio_id: int
    portfolio_base: str
    view_base: str
    exposures: List[CurrencyExposure]
    priced: int
    unpriced: int
    as_of: Optional[datetime]


def calculate_currency_exposure(
    portfolio_id: int,
    *,
    top_n: Optional[int] = None,
    view_base: Optional[str] = None,
) -> PortfolioExposureResult:
    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    positions = (
        session.query(Position)
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")

    if not positions:
        return PortfolioExposureResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            exposures=[],
            priced=0,
            unpriced=0,
            as_of=None,
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    rates_map, as_of = _latest_rates(session, canonical_base)

    if as_of is None or not rates_map:
        return PortfolioExposureResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            exposures=[],
            priced=0,
            unpriced=len(positions),
            as_of=None,
        )

    effective_rates = _rates_in_view_base(rates_map, canonical_base, resolved_view_base)

    totals: Dict[str, Dict[str, Decimal]] = {}
    priced = 0
    unpriced = 0
    context = get_decimal_context()
    with localcontext(context):
        for position in positions:
            currency = normalize_currency(position.currency_code)
            try:
                base_equiv = convert_position_amount(
                    native_amount=position.amount,
                    position_currency=currency,
                    portfolio_base=resolved_view_base,
                    rate_lookup=effective_rates,
                    side=position.side.value,
                )
            except RebaseError:
                unpriced += 1
                continue

            priced += 1
            bucket = totals.setdefault(
                currency,
                {"native": Decimal("0"), "base": Decimal("0")},
            )
            native_signed = convert_amount(position.amount, Decimal("1"), side=position.side.value)
            bucket["native"] += native_signed
            bucket["base"] += base_equiv

    exposures = [
        CurrencyExposure(currency_code=code, net_native=values["native"], base_equivalent=values["base"])
        for code, values in totals.items()
    ]
    exposures.sort(key=lambda item: abs(item.base_equivalent), reverse=True)

    if top_n is not None and top_n > 0 and len(exposures) > top_n:
        head = exposures[:top_n]
        tail = exposures[top_n:]
        other_native = sum(item.net_native for item in tail)
        other_base = sum(item.base_equivalent for item in tail)
        head.append(
            CurrencyExposure(
                currency_code="OTHER",
                net_native=other_native,
                base_equivalent=other_base,
            )
        )
        exposures = head

    return PortfolioExposureResult(
        portfolio_id=portfolio_id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        exposures=exposures,
        priced=priced,
        unpriced=unpriced,
        as_of=as_of,
    )



