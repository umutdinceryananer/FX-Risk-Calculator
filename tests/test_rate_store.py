from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.database import get_session
from app.models import FxRate
from app.providers.schemas import RateSnapshot
from app.services.rate_store import persist_snapshot


def test_persist_snapshot_normalizes_timestamp_to_utc(app):
    with app.app_context():
        session = get_session()
        session.query(FxRate).delete()
        session.commit()

        local_timestamp = datetime(2025, 1, 2, 3, 4, 5, tzinfo=ZoneInfo("Europe/Istanbul"))
        snapshot = RateSnapshot(
            base_currency="USD",
            source="mock",
            timestamp=local_timestamp,
            rates={"EUR": Decimal("0.9")},
        )

        persist_snapshot(snapshot)

        query = text(
            "SELECT timestamp FROM fx_rates "
            "WHERE base_currency_code = :base "
            "AND target_currency_code = :target "
            "AND source = :source"
        )
        raw_value = session.execute(
            query,
            {"base": "USD", "target": "EUR", "source": "mock"},
        ).scalar_one()

        expected_utc = local_timestamp.astimezone(UTC)
        expected_naive = expected_utc.replace(tzinfo=None)

        if isinstance(raw_value, str):
            assert raw_value.startswith(expected_naive.isoformat(sep=" "))
        else:
            assert raw_value == expected_utc

        stored = (
            session.query(FxRate)
            .filter_by(base_currency_code="USD", target_currency_code="EUR", source="mock")
            .one()
        )

        assert stored.timestamp == expected_naive

        session.query(FxRate).delete()
        session.commit()
