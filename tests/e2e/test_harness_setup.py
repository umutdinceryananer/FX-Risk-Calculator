from __future__ import annotations

from decimal import Decimal

from tests.e2e.providers import build_snapshot


def test_orchestrator_stub_registers_primary_snapshot(app, orchestrator_stub):
    snapshot = build_snapshot(
        base_currency="USD",
        source="primary-sequence",
        rates={"EUR": Decimal("0.92"), "GBP": Decimal("0.81")},
    )

    orchestrator, primary, fallback = orchestrator_stub(primary_latest=[snapshot])

    result = orchestrator.refresh_latest("usd")
    assert result == snapshot
    assert fallback is None

    assert len(primary.calls) == 1
    call = primary.calls[0]
    assert call.method == "get_latest"
    assert call.base == "USD"
    assert app.extensions["fx_orchestrator"] is orchestrator
