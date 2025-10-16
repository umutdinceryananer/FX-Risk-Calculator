"""Route handlers for health checks."""

from __future__ import annotations

from flask import Response, current_app, jsonify

from app.services.orchestrator import Orchestrator, SnapshotRecord

from . import bp


@bp.get("")
@bp.get("/")
def health() -> Response:
    """Return a basic readiness response for the service."""

    payload = {
        "status": "ok",
        "app": current_app.config.get("APP_NAME", "fx-risk-calculator"),
    }
    return jsonify(payload)


@bp.get("/rates")
def health_rates() -> Response:
    """Return the status of FX rates fetching components."""

    orchestrator: Orchestrator | None = current_app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
    record: SnapshotRecord | None = orchestrator.get_snapshot_info() if orchestrator else None

    if record is None:
        payload = {
            "status": "uninitialized",
            "source": None,
            "base_currency": None,
            "last_updated": None,
            "stale": None,
        }
    else:
        snapshot = record.snapshot
        payload = {
            "status": "ok",
            "source": snapshot.source,
            "base_currency": snapshot.base_currency,
            "last_updated": snapshot.timestamp.isoformat(),
            "stale": record.stale,
        }
    return jsonify(payload)
