"""Utilities for persisting FX rate snapshots."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.models import FxRate
from app.utils.datetime import ensure_utc


def persist_snapshot(snapshot) -> None:
    """Persist a RateSnapshot into the fx_rates table."""
    session = get_session()
    try:
        for currency_code, rate in snapshot.rates.items():
            timestamp = ensure_utc(snapshot.timestamp)
            _upsert_rate(
                session,
                base=snapshot.base_currency.upper(),
                target=currency_code.upper(),
                timestamp=timestamp,
                rate=Decimal(rate),
                source=snapshot.source,
            )
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise


def _upsert_rate(
    session,
    base: str,
    target: str,
    timestamp: datetime,
    rate: Decimal,
    source: str,
) -> None:
    existing = (
        session.query(FxRate)
        .filter_by(
            base_currency_code=base,
            target_currency_code=target,
            timestamp=timestamp,
            source=source,
        )
        .one_or_none()
    )
    if existing:
        existing.rate = rate
    else:
        session.add(
            FxRate(
                base_currency_code=base,
                target_currency_code=target,
                timestamp=timestamp,
                rate=rate,
                source=source,
            )
        )
