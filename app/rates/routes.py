"""Routes for manual FX rate refresh."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from flask import Response, current_app, jsonify

from app.providers.base import ProviderError
from app.services.rate_store import persist_snapshot
from app.services.orchestrator import Orchestrator
from app.services.scheduler import ensure_refresh_state

from . import bp

DEFAULT_THROTTLE_SECONDS = 60


@bp.post("/refresh")
def refresh_rates() -> Response:
    """Trigger a manual refresh of FX rates with throttle control."""

    app = current_app
    state = ensure_refresh_state(app)
    now = datetime.now(UTC)

    throttle_seconds = int(app.config.get("REFRESH_THROTTLE_SECONDS", DEFAULT_THROTTLE_SECONDS))
    throttle_seconds = max(throttle_seconds, 0)
    previous_window = state.get("throttle_window")

    throttle_until = state.get("throttle_until")
    window_matches = previous_window is None or previous_window == throttle_seconds

    if (
        throttle_seconds > 0
        and window_matches
        and isinstance(throttle_until, datetime)
        and throttle_until > now
    ):
        retry_after = max(int((throttle_until - now).total_seconds()), 1)
        payload = {
            "message": "Refresh throttled. Try again later.",
            "retry_after": retry_after,
        }
        return jsonify(payload), 429

    last_success = state.get("last_success")
    if throttle_seconds > 0 and window_matches and isinstance(last_success, datetime):
        next_allowed_at = last_success + timedelta(seconds=throttle_seconds)
        if next_allowed_at > now:
            state["throttle_until"] = next_allowed_at
            retry_after = max(int((next_allowed_at - now).total_seconds()), 1)
            payload = {
                "message": "Refresh throttled. Try again later.",
                "retry_after": retry_after,
            }
            return jsonify(payload), 429
    else:
        state.pop("throttle_until", None)

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
    if throttle_seconds > 0:
        state["throttle_until"] = now + timedelta(seconds=throttle_seconds)
    else:
        state.pop("throttle_until", None)
    state["throttle_window"] = throttle_seconds
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
