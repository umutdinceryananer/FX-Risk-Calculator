"""Routes for manual FX rate refresh."""

from __future__ import annotations

from datetime import UTC, datetime

from flask import Response, current_app, jsonify

from app.providers.base import ProviderError
from app.services.rate_store import persist_snapshot
from app.services.orchestrator import Orchestrator
from app.services.scheduler import ensure_refresh_state

from . import bp

THROTTLE_SECONDS = 60


@bp.post("/refresh")
def refresh_rates() -> Response:
    """Trigger a manual refresh of FX rates with throttle control."""

    app = current_app
    state = ensure_refresh_state(app)
    now = datetime.now(UTC)

    last_success = state.get("last_success")
    if last_success is not None and (now - last_success).total_seconds() < THROTTLE_SECONDS:
        retry_after = max(int(THROTTLE_SECONDS - (now - last_success).total_seconds()), 1)
        payload = {
            "message": "Refresh throttled. Try again later.",
            "retry_after": retry_after,
        }
        return jsonify(payload), 429

    orchestrator: Orchestrator | None = app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
    if orchestrator is None:
        return jsonify({"message": "Orchestrator unavailable."}), 503

    base = app.config.get("FX_CANONICAL_BASE", "USD")
    try:
        snapshot = orchestrator.refresh_latest(base)
    except ProviderError as exc:
        state["last_failure"] = now
        return jsonify({"message": str(exc)}), 503

    state["last_success"] = now
    state["last_failure"] = None
    persist_snapshot(snapshot)
    state["last_snapshot"] = {
        "source": snapshot.source,
        "base_currency": snapshot.base_currency,
        "timestamp": snapshot.timestamp.isoformat(),
    }

    payload = {
        "message": "Refresh triggered.",
        "source": snapshot.source,
        "base_currency": snapshot.base_currency,
        "as_of": snapshot.timestamp.isoformat(),
    }
    return jsonify(payload), 202



