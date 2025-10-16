"""Route handlers for health checks."""

from __future__ import annotations

from flask import current_app
from flask.views import MethodView

from app.schemas import HealthRatesSchema, HealthStatusSchema
from app.services.orchestrator import Orchestrator, SnapshotRecord

from . import blp


@blp.route("")
class HealthStatus(MethodView):
    @blp.response(200, HealthStatusSchema())
    def get(self):
        return {
            "status": "ok",
            "app": current_app.config.get("APP_NAME", "fx-risk-calculator"),
        }


@blp.route("/rates")
class HealthRates(MethodView):
    @blp.response(200, HealthRatesSchema())
    def get(self):
        orchestrator: Orchestrator | None = current_app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
        record: SnapshotRecord | None = orchestrator.get_snapshot_info() if orchestrator else None

        if record is None:
            return {
                "status": "uninitialized",
                "source": None,
                "base_currency": None,
                "last_updated": None,
                "stale": None,
            }

        snapshot = record.snapshot
        return {
            "status": "ok",
            "source": snapshot.source,
            "base_currency": snapshot.base_currency,
            "last_updated": snapshot.timestamp.isoformat(),
            "stale": record.stale,
        }
