from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.database import get_session
from app.models import FxRate, Portfolio, Position
from app.services.currency_registry import registry
from tests.factories import make_portfolio_payload, make_position_payload

from .providers import build_snapshot


def test_portfolio_happy_path_flow(app, client, orchestrator_stub):
    """Exercise the create->positions->refresh->metrics->what-if flow."""

    original_codes = set(registry.codes)
    registry.update({"USD", "EUR", "GBP"})

    snapshot_ts = datetime(2025, 10, 20, 12, 0, tzinfo=UTC)
    snapshot = build_snapshot(
        base_currency="USD",
        source="primary-sequence",
        rates={"EUR": Decimal("0.80"), "GBP": Decimal("0.50")},
        as_of=snapshot_ts,
    )
    orchestrator, primary_provider, _ = orchestrator_stub(primary_latest=[snapshot])

    portfolio_id: int | None = None
    try:
        portfolio_resp = client.post(
            "/api/v1/portfolios",
            json=make_portfolio_payload(name="E2E Flow Book", base_currency="USD"),
        )
        assert portfolio_resp.status_code == 201
        portfolio_data = portfolio_resp.get_json()
        portfolio_id = portfolio_data["id"]

        created_positions: list[int] = []
        position_payloads = [
            make_position_payload(currency_code="USD", amount=Decimal("100")),
            make_position_payload(currency_code="EUR", amount=Decimal("200")),
            make_position_payload(currency_code="GBP", amount=Decimal("50"), side="SHORT"),
        ]
        for payload in position_payloads:
            position_resp = client.post(
                f"/api/v1/portfolios/{portfolio_id}/positions",
                json=payload,
            )
            assert position_resp.status_code == 201
            created_positions.append(position_resp.get_json()["id"])

        assert len(created_positions) == 3

        refresh_resp = client.post("/rates/refresh")
        assert refresh_resp.status_code == 202
        refresh_payload = refresh_resp.get_json()
        assert refresh_payload["message"] == "Refresh triggered."
        assert refresh_payload["source"] == snapshot.source
        assert refresh_payload["base_currency"] == snapshot.base_currency
        assert _normalize_timestamp(refresh_payload["as_of"]) == snapshot_ts

        value_resp = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/value")
        assert value_resp.status_code == 200
        value_payload = value_resp.get_json()
        assert value_payload["portfolio_base"] == "USD"
        assert value_payload["view_base"] == "USD"
        assert value_payload["priced"] == 3
        assert value_payload["unpriced"] == 0
        assert value_payload["unpriced_reasons"] == {}
        assert _normalize_timestamp(value_payload["as_of"]) == snapshot_ts
        assert Decimal(value_payload["value"]) == Decimal("250.00")

        value_eur_resp = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/value?base=eur")
        assert value_eur_resp.status_code == 200
        value_eur_payload = value_eur_resp.get_json()
        assert value_eur_payload["view_base"] == "EUR"
        assert Decimal(value_eur_payload["value"]) == Decimal("200.00")

        exposure_resp = client.get(f"/api/v1/metrics/portfolio/{portfolio_id}/exposure?top_n=2")
        assert exposure_resp.status_code == 200
        exposure_payload = exposure_resp.get_json()
        assert exposure_payload["view_base"] == "USD"
        exposures = exposure_payload["exposures"]
        assert len(exposures) == 3
        assert exposures[0]["currency_code"] == "EUR"
        assert Decimal(exposures[0]["net_native"]) == Decimal("200.0000")
        assert Decimal(exposures[0]["base_equivalent"]) == Decimal("250.00")
        assert exposures[-1]["currency_code"] == "OTHER"
        trailing_pairs = {
            (Decimal(item["base_equivalent"]), Decimal(item["net_native"]))
            for item in exposures[1:]
        }
        assert trailing_pairs == {
            (Decimal("100.00"), Decimal("100.0000")),
            (Decimal("-100.00"), Decimal("-50.0000")),
        }

        whatif_resp = client.post(
            f"/api/v1/metrics/portfolio/{portfolio_id}/whatif",
            json={"currency": "EUR", "shock_pct": "5"},
        )
        assert whatif_resp.status_code == 200
        whatif_payload = whatif_resp.get_json()
        assert whatif_payload["portfolio_id"] == portfolio_id
        assert whatif_payload["view_base"] == "USD"
        assert whatif_payload["shocked_currency"] == "EUR"
        assert whatif_payload["shock_pct"] == "5"
        assert Decimal(whatif_payload["current_value"]) == Decimal("250.00")
        assert Decimal(whatif_payload["new_value"]) == Decimal("262.50")
        assert Decimal(whatif_payload["delta_value"]) == Decimal("12.50")
        assert _normalize_timestamp(whatif_payload["as_of"]) == snapshot_ts

        assert len(primary_provider.calls) == 1
        assert primary_provider.calls[0].method == "get_latest"
        assert primary_provider.calls[0].base == "USD"
        assert app.extensions["fx_orchestrator"] is orchestrator
    finally:
        registry.codes = original_codes
        with app.app_context():
            session = get_session()
            if portfolio_id is not None:
                session.query(Position).filter(Position.portfolio_id == portfolio_id).delete()
                session.query(Portfolio).filter(Portfolio.id == portfolio_id).delete()
            session.query(FxRate).filter(
                FxRate.base_currency_code == snapshot.base_currency,
                FxRate.timestamp == snapshot_ts,
                FxRate.source == snapshot.source,
            ).delete()
            session.commit()


def _normalize_timestamp(raw_value: str) -> datetime:
    parsed = datetime.fromisoformat(raw_value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
