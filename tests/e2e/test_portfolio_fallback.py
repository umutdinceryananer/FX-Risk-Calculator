from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.database import get_session
from app.models import FxRate, Portfolio, Position
from app.providers import ProviderError
from app.services.currency_registry import registry
from tests.factories import make_portfolio_payload, make_position_payload

from .providers import build_snapshot
from .test_portfolio_happy_path import _normalize_timestamp


def test_portfolio_refresh_uses_fallback_provider(app, client, orchestrator_stub):
    """Ensure the orchestrator falls back when the primary provider fails."""

    original_codes = set(registry.codes)
    registry.update({"USD", "EUR", "GBP"})
    previous_throttle = app.config.get("REFRESH_THROTTLE_SECONDS")
    app.config["REFRESH_THROTTLE_SECONDS"] = 0
    refresh_state = app.extensions.get("fx_refresh_state")
    if isinstance(refresh_state, dict):
        refresh_state.clear()

    fallback_snapshot_ts = datetime(2025, 10, 21, 8, 30, tzinfo=UTC)
    fallback_snapshot = build_snapshot(
        base_currency="USD",
        source="fallback-sequence",
        rates={"EUR": Decimal("0.80"), "GBP": Decimal("0.50")},
        as_of=fallback_snapshot_ts,
    )
    orchestrator, primary_provider, fallback_provider = orchestrator_stub(
        primary_latest=[ProviderError("primary down")],
        fallback_latest=[fallback_snapshot],
    )
    assert fallback_provider is not None

    portfolio_id: int | None = None
    try:
        create_resp = client.post(
            "/api/v1/portfolios",
            json=make_portfolio_payload(name="Fallback Flow Book", base_currency="USD"),
        )
        assert create_resp.status_code == 201
        portfolio_id = create_resp.get_json()["id"]

        for payload in (
            make_position_payload(currency_code="USD", amount=Decimal("100")),
            make_position_payload(currency_code="EUR", amount=Decimal("200")),
            make_position_payload(currency_code="GBP", amount=Decimal("50"), side="SHORT"),
        ):
            position_resp = client.post(
                f"/api/v1/portfolios/{portfolio_id}/positions", json=payload
            )
            assert position_resp.status_code == 201

        refresh_resp = client.post("/rates/refresh")
        assert refresh_resp.status_code == 202
        refresh_payload = refresh_resp.get_json()
        assert refresh_payload["source"] == fallback_snapshot.source
        assert refresh_payload["base_currency"] == fallback_snapshot.base_currency
        assert _normalize_timestamp(refresh_payload["as_of"]) == fallback_snapshot_ts

        assert len(primary_provider.calls) == 1
        assert primary_provider.calls[0].method == "get_latest"
        assert len(fallback_provider.calls) == 1
        assert fallback_provider.calls[0].method == "get_latest"
        assert fallback_provider.calls[0].base == "USD"
        assert app.extensions["fx_orchestrator"] is orchestrator

        value_resp = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/value")
        assert value_resp.status_code == 200
        value_payload = value_resp.get_json()
        assert value_payload["view_base"] == "USD"
        assert _normalize_timestamp(value_payload["as_of"]) == fallback_snapshot_ts
        assert Decimal(value_payload["value"]) == Decimal("250.00")
        assert value_payload["unpriced"] == 0

        exposure_resp = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/exposure")
        assert exposure_resp.status_code == 200
        exposure_payload = exposure_resp.get_json()
        assert exposure_payload["view_base"] == "USD"
        exposures = exposure_payload["exposures"]
        assert len(exposures) == 3
        assert exposures[0]["currency_code"] == "EUR"
        trailing_pairs = {
            (Decimal(item["base_equivalent"]), Decimal(item["net_native"]))
            for item in exposures[1:]
        }
        assert trailing_pairs == {
            (Decimal("100.00"), Decimal("100.0000")),
            (Decimal("-100.00"), Decimal("-50.0000")),
        }
        assert exposure_payload["unpriced"] == 0

        with app.app_context():
            session = get_session()
            stored_rates = (
                session.query(FxRate)
                .filter(
                    FxRate.timestamp == fallback_snapshot_ts,
                    FxRate.source == fallback_snapshot.source,
                )
                .all()
            )
            assert stored_rates, "Fallback snapshot should be persisted to fx_rates"
    finally:
        registry.codes = original_codes
        if previous_throttle is None:
            app.config.pop("REFRESH_THROTTLE_SECONDS", None)
        else:
            app.config["REFRESH_THROTTLE_SECONDS"] = previous_throttle
        with app.app_context():
            session = get_session()
            if portfolio_id is not None:
                session.query(Position).filter(Position.portfolio_id == portfolio_id).delete()
                session.query(Portfolio).filter(Portfolio.id == portfolio_id).delete()
            session.query(FxRate).filter(
                FxRate.timestamp == fallback_snapshot_ts,
                FxRate.source == fallback_snapshot.source,
            ).delete()
            session.commit()
