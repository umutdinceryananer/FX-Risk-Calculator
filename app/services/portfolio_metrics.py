"""Service helpers for calculating portfolio metrics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, date
from decimal import Decimal, localcontext
from typing import DefaultDict, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from flask import current_app
from sqlalchemy import desc
from sqlalchemy.orm import load_only

from app.database import get_session
from app.errors import APIError, ValidationError
from app.models import FxRate, Portfolio, Position
from app.services.fx_conversion import (
    RebaseError,
    convert_amount,
    convert_position_amount,
    get_decimal_context,
    normalize_currency,
    rebase_rates,
    to_decimal,
    quantize_amount,
)
from app.validation import validate_currency_code
from app.services.currency_registry import registry


UNPRICED_REASON_MISSING_RATE = "missing_rate"
UNPRICED_REASON_UNKNOWN_CURRENCY = "unknown_currency"


@dataclass(frozen=True)
class PortfolioValueResult:
    """Calculated portfolio value expressed in a target base currency."""

    portfolio_id: int
    portfolio_base: str
    view_base: str
    value: Decimal
    priced: int
    unpriced: int
    unpriced_reasons: Dict[str, List[str]]
    as_of: Optional[datetime]


@dataclass(frozen=True)
class PortfolioValueSeriesPoint:
    date: date
    value: Decimal


@dataclass(frozen=True)
class PortfolioValueSeriesResult:
    portfolio_id: int
    portfolio_base: str
    view_base: str
    series: List[PortfolioValueSeriesPoint]


def _fetch_positions(session, portfolio_id: int) -> List[Position]:
    """Return portfolio positions with only the required columns loaded."""

    return (
        session.query(Position)
        .options(load_only(Position.currency_code, Position.amount, Position.side))
        .filter(Position.portfolio_id == portfolio_id)
        .all()
    )


def calculate_portfolio_value(
    portfolio_id: int, *, view_base: Optional[str] = None
) -> PortfolioValueResult:
    """Compute aggregate portfolio value in the requested base currency."""

    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")

    positions = _fetch_positions(session, portfolio.id)

    if not positions:
        return PortfolioValueResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            value=quantize_amount(Decimal("0")),
            priced=0,
            unpriced=0,
            unpriced_reasons={},
            as_of=None,
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    rates_map, as_of = _latest_rates(session, canonical_base)

    if as_of is None or not rates_map:
        reason_map = _init_reason_map()
        for position in positions:
            _add_reason(reason_map, UNPRICED_REASON_MISSING_RATE, position.currency_code)
        return PortfolioValueResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            value=quantize_amount(Decimal("0")),
            priced=0,
            unpriced=len(positions),
            unpriced_reasons=_serialize_reason_map(reason_map),
            as_of=None,
        )

    effective_rates = _rates_in_view_base(
        rates_map,
        canonical_base,
        resolved_view_base,
        as_of=as_of,
    )

    total, priced, unpriced, reason_map = _portfolio_value_from_rates(
        positions,
        resolved_view_base,
        effective_rates,
    )
    total = quantize_amount(total)

    return PortfolioValueResult(
        portfolio_id=portfolio.id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        value=total,
        priced=priced,
        unpriced=unpriced,
        unpriced_reasons=_serialize_reason_map(reason_map),
        as_of=as_of,
    )


def _rates_for_timestamps(
    session,
    canonical_base: str,
    timestamps: Iterable[datetime],
) -> Dict[datetime, Dict[str, Decimal]]:
    base_code = normalize_currency(canonical_base)
    ordered_lookup = list(dict.fromkeys(timestamps))
    if not ordered_lookup:
        return {}

    grouped: Dict[datetime, Dict[str, Decimal]] = {
        _to_utc_datetime(ts): {} for ts in ordered_lookup
    }

    rows = (
        session.query(FxRate.timestamp, FxRate.target_currency_code, FxRate.rate)
        .filter(
            FxRate.base_currency_code == canonical_base,
            FxRate.timestamp.in_(ordered_lookup),
        )
        .all()
    )

    for row_timestamp, target_code, rate in rows:
        normalized_ts = _to_utc_datetime(row_timestamp)
        rates = grouped.setdefault(normalized_ts, {})
        rates[normalize_currency(target_code)] = rate

    for normalized_ts, rates in grouped.items():
        if rates:
            rates[base_code] = Decimal("1")

    return grouped


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

    rates_map = _rates_for_timestamps(session, canonical_base, [latest_timestamp])
    normalized_ts = _to_utc_datetime(latest_timestamp)
    return rates_map.get(normalized_ts, {}), latest_timestamp


def _missing_view_base_error(view_base: str, as_of: Optional[datetime]) -> ValidationError:
    as_of_iso = _to_utc_datetime(as_of).isoformat() if as_of is not None else None
    return ValidationError(
        "FX rates are unavailable for the requested base currency.",
        payload={
            "field": "base",
            "view_base": normalize_currency(view_base),
            "as_of": as_of_iso,
        },
    )


def _rates_in_view_base(
    rates_map: Dict[str, Decimal],
    canonical_base: str,
    view_base: str,
    *,
    as_of: Optional[datetime] = None,
) -> Dict[str, Decimal]:
    canonical_norm = normalize_currency(canonical_base)
    view_norm = normalize_currency(view_base)

    normalized_rates: Dict[str, Decimal] = {}
    for code, value in rates_map.items():
        normalized_rates[normalize_currency(code)] = to_decimal(value)
    normalized_rates.setdefault(canonical_norm, Decimal("1"))

    if view_norm != canonical_norm and view_norm not in normalized_rates:
        raise _missing_view_base_error(view_norm, as_of)

    if view_norm == canonical_norm:
        source_rates = dict(normalized_rates)
    else:
        try:
            source_rates = rebase_rates(normalized_rates, view_norm)
        except RebaseError as exc:
            raise _missing_view_base_error(view_norm, as_of) from exc
        source_rates = dict(source_rates)
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


def _init_reason_map() -> DefaultDict[str, Set[str]]:
    return defaultdict(set)


def _add_reason(
    reason_map: DefaultDict[str, Set[str]],
    reason: str,
    currency_code: Optional[str],
) -> None:
    if not currency_code:
        return
    normalized = str(currency_code).strip().upper()
    if normalized:
        reason_map[reason].add(normalized)


def _serialize_reason_map(reason_map: Mapping[str, Set[str]]) -> Dict[str, List[str]]:
    return {reason: sorted(codes) for reason, codes in reason_map.items() if codes}


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
    unpriced_reasons: Dict[str, List[str]]


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

    positions = _fetch_positions(session, portfolio_id)

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
            unpriced_reasons={},
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    rates_map, as_of = _latest_rates(session, canonical_base)

    reason_map = _init_reason_map()

    if as_of is None or not rates_map:
        for position in positions:
            _add_reason(reason_map, UNPRICED_REASON_MISSING_RATE, position.currency_code)
        return PortfolioExposureResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            exposures=[],
            priced=0,
            unpriced=len(positions),
            as_of=None,
            unpriced_reasons=_serialize_reason_map(reason_map),
        )

    effective_rates = _rates_in_view_base(
        rates_map,
        canonical_base,
        resolved_view_base,
        as_of=as_of,
    )

    totals: Dict[str, Dict[str, Decimal]] = {}
    priced = 0
    unpriced = 0
    context = get_decimal_context()
    with localcontext(context):
        for position in positions:
            try:
                currency = normalize_currency(position.currency_code)
            except ValueError:
                currency = str(position.currency_code).strip().upper()
                unpriced += 1
                _add_reason(reason_map, UNPRICED_REASON_UNKNOWN_CURRENCY, currency)
                continue

            if not registry.is_allowed(currency):
                unpriced += 1
                _add_reason(reason_map, UNPRICED_REASON_UNKNOWN_CURRENCY, currency)
                continue

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
                _add_reason(reason_map, UNPRICED_REASON_MISSING_RATE, currency)
                continue

            priced += 1
            bucket = totals.setdefault(
                currency,
                {"native": Decimal("0"), "base": Decimal("0")},
            )
            native_signed = convert_amount(position.amount, Decimal("1"), side=position.side.value)
            bucket["native"] += native_signed
            bucket["base"] += base_equiv

    exposures: List[CurrencyExposure] = []
    for code, values in totals.items():
        exposures.append(
            CurrencyExposure(
                currency_code=code,
                net_native=quantize_amount(values["native"], places=4),
                base_equivalent=quantize_amount(values["base"]),
            )
        )
    exposures.sort(key=lambda item: abs(item.base_equivalent), reverse=True)

    if top_n is not None and top_n > 0 and len(exposures) > top_n:
        head = exposures[:top_n]
        tail = exposures[top_n:]
        other_native = quantize_amount(sum(item.net_native for item in tail), places=4)
        other_base = quantize_amount(sum(item.base_equivalent for item in tail))
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
        unpriced_reasons=_serialize_reason_map(reason_map),
    )


@dataclass(frozen=True)
class PortfolioDailyPnLResult:
    portfolio_id: int
    portfolio_base: str
    view_base: str
    pnl: Decimal
    value_current: Decimal
    value_previous: Optional[Decimal]
    as_of: Optional[datetime]
    prev_date: Optional[datetime]
    positions_changed: bool
    priced_current: int
    unpriced_current: int
    priced_previous: int
    unpriced_previous: int
    unpriced_reasons_current: Dict[str, List[str]]
    unpriced_reasons_previous: Dict[str, List[str]]


@dataclass(frozen=True)
class PortfolioWhatIfResult:
    portfolio_id: int
    portfolio_base: str
    view_base: str
    shocked_currency: str
    shock_pct: Decimal
    current_value: Decimal
    new_value: Decimal
    delta_value: Decimal
    as_of: Optional[datetime]


def calculate_daily_pnl(
    portfolio_id: int,
    *,
    view_base: Optional[str] = None,
) -> PortfolioDailyPnLResult:
    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    positions = _fetch_positions(session, portfolio_id)

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")

    if not positions:
        zero = quantize_amount(Decimal("0"))
        return PortfolioDailyPnLResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            pnl=zero,
            value_current=zero,
            value_previous=None,
            as_of=None,
            prev_date=None,
            positions_changed=False,
            priced_current=0,
            unpriced_current=0,
            priced_previous=0,
            unpriced_previous=0,
            unpriced_reasons_current={},
            unpriced_reasons_previous={},
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    latest_timestamp, previous_timestamp = _latest_two_timestamps(session, canonical_base)

    reason_map_current = _init_reason_map()
    reason_map_previous = _init_reason_map()

    if latest_timestamp is None or previous_timestamp is None:
        zero = quantize_amount(Decimal("0"))
        for position in positions:
            _add_reason(reason_map_current, UNPRICED_REASON_MISSING_RATE, position.currency_code)
            _add_reason(reason_map_previous, UNPRICED_REASON_MISSING_RATE, position.currency_code)
        return PortfolioDailyPnLResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            pnl=zero,
            value_current=zero,
            value_previous=None,
            as_of=latest_timestamp,
            prev_date=previous_timestamp,
            positions_changed=False,
            priced_current=0,
            unpriced_current=len(positions),
            priced_previous=0,
            unpriced_previous=len(positions),
            unpriced_reasons_current=_serialize_reason_map(reason_map_current),
            unpriced_reasons_previous=_serialize_reason_map(reason_map_previous),
        )

    latest_rates = _rates_for_timestamp(session, canonical_base, latest_timestamp)
    previous_rates = _rates_for_timestamp(session, canonical_base, previous_timestamp)

    if not latest_rates or not previous_rates:
        zero = quantize_amount(Decimal("0"))
        for position in positions:
            _add_reason(reason_map_current, UNPRICED_REASON_MISSING_RATE, position.currency_code)
            _add_reason(reason_map_previous, UNPRICED_REASON_MISSING_RATE, position.currency_code)
        return PortfolioDailyPnLResult(
            portfolio_id=portfolio_id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            pnl=zero,
            value_current=zero,
            value_previous=None,
            as_of=latest_timestamp,
            prev_date=previous_timestamp,
            positions_changed=False,
            priced_current=0,
            unpriced_current=len(positions),
            priced_previous=0,
            unpriced_previous=len(positions),
            unpriced_reasons_current=_serialize_reason_map(reason_map_current),
            unpriced_reasons_previous=_serialize_reason_map(reason_map_previous),
        )

    effective_latest = _rates_in_view_base(
        latest_rates,
        canonical_base,
        resolved_view_base,
        as_of=latest_timestamp,
    )
    effective_previous = _rates_in_view_base(
        previous_rates,
        canonical_base,
        resolved_view_base,
        as_of=previous_timestamp,
    )

    value_current, priced_current, unpriced_current, reason_map_current = (
        _portfolio_value_from_rates(
            positions,
            resolved_view_base,
            effective_latest,
        )
    )
    value_previous, priced_previous, unpriced_previous, reason_map_previous = (
        _portfolio_value_from_rates(
            positions,
            resolved_view_base,
            effective_previous,
        )
    )

    value_current = quantize_amount(value_current)
    value_previous = quantize_amount(value_previous) if value_previous is not None else None
    pnl = (
        quantize_amount(value_current - value_previous)
        if value_previous is not None
        else value_current
    )

    return PortfolioDailyPnLResult(
        portfolio_id=portfolio_id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        pnl=pnl,
        value_current=value_current,
        value_previous=value_previous,
        as_of=(
            latest_timestamp.replace(tzinfo=UTC)
            if latest_timestamp.tzinfo is None
            else latest_timestamp
        ),
        prev_date=(
            previous_timestamp.replace(tzinfo=UTC)
            if previous_timestamp.tzinfo is None
            else previous_timestamp
        ),
        positions_changed=False,
        priced_current=priced_current,
        unpriced_current=unpriced_current,
        priced_previous=priced_previous,
        unpriced_previous=unpriced_previous,
        unpriced_reasons_current=_serialize_reason_map(reason_map_current),
        unpriced_reasons_previous=_serialize_reason_map(reason_map_previous),
    )


def calculate_portfolio_value_series(
    portfolio_id: int,
    *,
    view_base: Optional[str] = None,
    days: int = 30,
) -> PortfolioValueSeriesResult:
    if days < 1 or days > 365:
        raise ValidationError(
            "'days' must be between 1 and 365.",
            payload={"field": "days"},
        )

    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    positions = _fetch_positions(session, portfolio.id)

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")

    if not positions:
        return PortfolioValueSeriesResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            series=[],
        )

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    timestamps = _recent_daily_timestamps(session, canonical_base, days)

    if not timestamps:
        return PortfolioValueSeriesResult(
            portfolio_id=portfolio.id,
            portfolio_base=portfolio_base,
            view_base=resolved_view_base,
            series=[],
        )

    rates_by_timestamp = _rates_for_timestamps(session, canonical_base, timestamps)

    series: List[PortfolioValueSeriesPoint] = []
    for timestamp in timestamps:
        normalized_timestamp = _to_utc_datetime(timestamp)
        rates_map = rates_by_timestamp.get(normalized_timestamp)
        if not rates_map:
            continue

        effective_rates = _rates_in_view_base(
            rates_map,
            canonical_base,
            resolved_view_base,
            as_of=normalized_timestamp,
        )
        value, priced, _, _ = _portfolio_value_from_rates(
            positions,
            resolved_view_base,
            effective_rates,
        )

        if priced == 0:
            continue

        point_date = normalized_timestamp.date()
        series.append(
            PortfolioValueSeriesPoint(
                date=point_date,
                value=quantize_amount(value),
            )
        )

    return PortfolioValueSeriesResult(
        portfolio_id=portfolio.id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        series=series,
    )


def simulate_currency_shock(
    portfolio_id: int,
    *,
    currency: str,
    shock_pct: Decimal,
    view_base: Optional[str] = None,
) -> PortfolioWhatIfResult:
    """Evaluate the impact of a single-currency shock on portfolio value."""

    session = get_session()
    portfolio: Optional[Portfolio] = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)

    positions = _fetch_positions(session, portfolio_id)

    if not positions:
        raise ValidationError(
            "Portfolio has no positions to simulate.",
            payload={"field": "portfolio_id"},
        )

    portfolio_base = normalize_currency(portfolio.base_currency_code)
    resolved_view_base = validate_currency_code(view_base or portfolio_base, field="base")
    shocked_currency = validate_currency_code(currency, field="currency")

    context = get_decimal_context()
    with localcontext(context):
        pct_decimal = to_decimal(shock_pct)
        if pct_decimal < Decimal("-10") or pct_decimal > Decimal("10"):
            raise ValidationError(
                "'shock_pct' must be between -10 and 10.",
                payload={"field": "shock_pct"},
            )
        shock_factor = Decimal("1") + (pct_decimal / Decimal("100"))

    canonical_base = normalize_currency(current_app.config.get("FX_CANONICAL_BASE", "USD"))
    rates_map, as_of = _latest_rates(session, canonical_base)

    if as_of is None or not rates_map:
        raise ValidationError(
            "FX rates are unavailable for simulation.",
            payload={"field": "rates"},
        )

    effective_rates = _rates_in_view_base(
        rates_map,
        canonical_base,
        resolved_view_base,
        as_of=as_of,
    )

    current_value, priced, unpriced, reason_map_current = _portfolio_value_from_rates(
        positions,
        resolved_view_base,
        effective_rates,
    )

    if unpriced > 0:
        raise ValidationError(
            "Unable to price all positions with current FX rates.",
            payload={
                "unpriced_positions": unpriced,
                "reasons": _serialize_reason_map(reason_map_current),
            },
        )

    base_rate = effective_rates.get(shocked_currency)
    if base_rate is None:
        raise ValidationError(
            f"Missing FX rate for currency '{shocked_currency}'.",
            payload={"field": "currency"},
        )

    shocked_rates = _apply_currency_shock(
        effective_rates,
        shocked_currency,
        shock_factor,
    )

    new_value, priced_new, unpriced_new, reason_map_new = _portfolio_value_from_rates(
        positions,
        resolved_view_base,
        shocked_rates,
    )

    if unpriced_new > 0:
        raise ValidationError(
            "Unable to price all positions with shocked FX rates.",
            payload={
                "unpriced_positions": unpriced_new,
                "reasons": _serialize_reason_map(reason_map_new),
            },
        )

    with localcontext(context):
        delta_value = new_value - current_value

    return PortfolioWhatIfResult(
        portfolio_id=portfolio_id,
        portfolio_base=portfolio_base,
        view_base=resolved_view_base,
        shocked_currency=shocked_currency,
        shock_pct=pct_decimal,
        current_value=current_value,
        new_value=new_value,
        delta_value=delta_value,
        as_of=as_of,
    )


def _latest_two_timestamps(
    session, canonical_base: str
) -> Tuple[Optional[datetime], Optional[datetime]]:
    rows = (
        session.query(FxRate.timestamp)
        .filter(FxRate.base_currency_code == canonical_base)
        .order_by(desc(FxRate.timestamp))
        .distinct()
        .limit(2)
        .all()
    )
    timestamps = [row[0] for row in rows]
    if not timestamps:
        return None, None
    if len(timestamps) == 1:
        return timestamps[0], None
    return timestamps[0], timestamps[1]


def _rates_for_timestamp(session, canonical_base: str, timestamp: datetime) -> Dict[str, Decimal]:
    rates_map = _rates_for_timestamps(session, canonical_base, [timestamp])
    return rates_map.get(_to_utc_datetime(timestamp), {})


def _portfolio_value_from_rates(
    positions: List[Position],
    view_base: str,
    rate_lookup: Dict[str, Decimal],
) -> Tuple[Decimal, int, int, DefaultDict[str, Set[str]]]:
    total = Decimal("0")
    priced = 0
    unpriced = 0
    reason_map = _init_reason_map()
    context = get_decimal_context()
    with localcontext(context):
        for position in positions:
            try:
                normalized_currency = normalize_currency(position.currency_code)
            except ValueError:
                normalized_currency = str(position.currency_code).strip().upper()
                unpriced += 1
                _add_reason(reason_map, UNPRICED_REASON_UNKNOWN_CURRENCY, normalized_currency)
                continue

            if not registry.is_allowed(normalized_currency):
                unpriced += 1
                _add_reason(reason_map, UNPRICED_REASON_UNKNOWN_CURRENCY, normalized_currency)
                continue

            try:
                converted = convert_position_amount(
                    native_amount=position.amount,
                    position_currency=normalized_currency,
                    portfolio_base=view_base,
                    rate_lookup=rate_lookup,
                    side=position.side.value,
                )
            except RebaseError:
                unpriced += 1
                _add_reason(reason_map, UNPRICED_REASON_MISSING_RATE, normalized_currency)
                continue

            priced += 1
            total += converted
    return total, priced, unpriced, reason_map


def _recent_daily_timestamps(session, canonical_base: str, days: int) -> List[datetime]:
    """Return the most recent FX timestamps for distinct calendar days."""

    multiplier = max(3, min(10, days))
    rows = (
        session.query(FxRate.timestamp)
        .filter(FxRate.base_currency_code == canonical_base)
        .order_by(desc(FxRate.timestamp))
        .limit(days * multiplier)
        .all()
    )

    seen_dates: set[date] = set()
    timestamps: List[datetime] = []

    for (raw_timestamp,) in rows:
        if raw_timestamp is None:
            continue
        normalized = _to_utc_datetime(raw_timestamp)
        day_key = normalized.date()
        if day_key in seen_dates:
            continue
        seen_dates.add(day_key)
        timestamps.append(normalized)
        if len(timestamps) >= days:
            break

    timestamps.sort()
    return timestamps


def _to_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _apply_currency_shock(
    rates: Mapping[str, Decimal],
    currency: str,
    shock_factor: Decimal,
) -> Dict[str, Decimal]:
    """Return a new rates mapping with the specified currency shocked."""

    normalized_currency = normalize_currency(currency)
    context = get_decimal_context()
    with localcontext(context):
        shocked: Dict[str, Decimal] = {}
        for code, value in rates.items():
            code_norm = normalize_currency(code)
            rate_value = to_decimal(value)
            if code_norm == normalized_currency:
                shocked[code_norm] = rate_value * shock_factor
            else:
                shocked[code_norm] = rate_value
    return shocked
