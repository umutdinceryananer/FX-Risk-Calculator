"""Scheduler setup for periodic FX rate refresh."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.providers import ProviderError

logger = logging.getLogger(__name__)

SCHEDULER_EXT_KEY = "apscheduler"
REFRESH_STATE_KEY = "fx_refresh_state"


def ensure_refresh_state(app) -> dict:
    """Ensure refresh state dict exists on app extensions."""

    return app.extensions.setdefault(REFRESH_STATE_KEY, {})


def _run_refresh(app) -> None:
    from app.services.orchestrator import Orchestrator  # Local import to avoid circular

    with app.app_context():
        orchestrator: Optional[Orchestrator] = app.extensions.get("fx_orchestrator")  # type: ignore[assignment]
        if orchestrator is None:
            logger.warning("No orchestrator configured; skipping scheduled refresh.")
            return

        base = app.config.get("FX_CANONICAL_BASE", "USD")
        try:
            snapshot = orchestrator.refresh_latest(base)
            state = ensure_refresh_state(app)
            state["last_success"] = datetime.now(UTC)
            state["last_failure"] = None
            state["last_snapshot"] = {
                "source": snapshot.source,
                "base_currency": snapshot.base_currency,
                "timestamp": snapshot.timestamp.isoformat(),
            }
            logger.info("Scheduled refresh completed using %s", snapshot.source)
        except ProviderError as exc:
            state = ensure_refresh_state(app)
            state["last_failure"] = datetime.now(UTC)
            logger.error("Scheduled refresh failed: %s", exc)


def init_scheduler(app) -> Optional[BackgroundScheduler]:
    """Initialise APScheduler with periodic refresh job if enabled."""

    ensure_refresh_state(app)

    if not app.config.get("SCHEDULER_ENABLED", True):
        logger.info("Scheduler disabled via configuration.")
        return None

    if app.extensions.get(SCHEDULER_EXT_KEY):
        return app.extensions[SCHEDULER_EXT_KEY]

    scheduler = BackgroundScheduler(timezone=app.config.get("SCHEDULER_TIMEZONE", "UTC"))
    cron_expr = app.config.get("RATES_REFRESH_CRON", "0 */1 * * *")
    trigger = CronTrigger.from_crontab(cron_expr)
    scheduler.add_job(_run_refresh, trigger=trigger, args=[app], id="refresh_rates", replace_existing=True)
    scheduler.start()

    app.extensions[SCHEDULER_EXT_KEY] = scheduler

    @app.teardown_appcontext
    def _shutdown_scheduler(_exc: Optional[BaseException]) -> None:
        sched = app.extensions.get(SCHEDULER_EXT_KEY)
        if sched and getattr(sched, "running", False):
            sched.shutdown(wait=False)

    logger.info("APScheduler started with cron '%s'", cron_expr)
    return scheduler
