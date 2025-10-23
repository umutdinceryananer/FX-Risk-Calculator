# ruff: noqa: S607,S603
"""Sanity check helper for Issue #38.

Run this script locally to populate a representative dataset (~2k positions)
and capture timing data for the key metrics endpoints. It assumes the usual
development configuration (SQLite) and can be executed repeatedly; subsequent
runs will reuse the seeded portfolio unless `--reset` is supplied.
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
import time
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text

sys.path.append(os.fspath(os.getcwd()))

from app import create_app  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Currency, FxRate, Portfolio, Position, PositionType  # noqa: E402
from app.services import (  # noqa: E402
    PortfolioCreateData,
    PositionCreateData,
    create_portfolio,
    create_position,
)

DEFAULT_POSITIONS = 2000
PORTFOLIO_NAME = "Perf Sample Portfolio"


@dataclass(slots=True)
class TimingResult:
    name: str
    duration_ms: float
    status_code: int


def _generate_amount() -> Decimal:
    base = random.uniform(500, 10_000)
    return Decimal(str(round(base, 2)))


def _choose_side() -> PositionType:
    return random.choice([PositionType.LONG, PositionType.SHORT])


def _resolve_currencies(session) -> list[str]:
    rows = session.query(Currency.code).order_by(Currency.code).all()
    codes = [row[0] for row in rows if row[0].upper() != "USD"]
    if not codes:
        raise RuntimeError("Currency table is empty; run migrations/seed first.")
    return codes


def _ensure_portfolio(session, positions_target: int, currencies: list[str]) -> Portfolio:
    existing = session.query(Portfolio).filter(Portfolio.name == PORTFOLIO_NAME).one_or_none()
    if existing:
        current_count = session.query(Position).filter(Position.portfolio_id == existing.id).count()
        if current_count >= positions_target:
            return existing

    dto = create_portfolio(
        PortfolioCreateData(
            name=PORTFOLIO_NAME,
            base_currency="USD",
        )
    )
    portfolio = session.query(Portfolio).get(dto.id)
    assert portfolio is not None
    session.flush()

    for chunk in _batched(range(positions_target), 500):
        for _ in chunk:
            currency = random.choice(currencies)
            create_position(
                PositionCreateData(
                    portfolio_id=portfolio.id,
                    currency_code=currency,
                    amount=_generate_amount(),
                    side=_choose_side(),
                )
            )
        session.flush()

    return portfolio


def _batched(iterable: Iterable[int], size: int) -> Iterable[list[int]]:
    batch: list[int] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _ensure_rates(session, currencies: list[str]) -> None:
    timestamp = datetime.now(tz=UTC).replace(microsecond=0)
    existing = (
        session.query(FxRate)
        .filter(FxRate.base_currency_code == "USD", FxRate.timestamp == timestamp)
        .count()
    )
    if existing >= len(currencies):
        return

    session.query(FxRate).filter(FxRate.base_currency_code == "USD").delete()
    session.flush()

    for code in currencies:
        rate = Decimal(str(round(random.uniform(0.2, 1.3), 6)))
        session.add(
            FxRate(
                base_currency_code="USD",
                target_currency_code=code.upper(),
                rate=rate,
                timestamp=timestamp,
                source="perf_fixture",
            )
        )
    session.flush()


@contextmanager
def _app_context():
    app = create_app(os.environ.get("APP_ENV", "development"))
    with app.app_context():
        yield app


def _time_request(client, method: str, path: str, *, name: str) -> TimingResult:
    start = time.perf_counter()
    response = client.open(path, method=method)
    duration_ms = (time.perf_counter() - start) * 1000
    return TimingResult(name=name, duration_ms=duration_ms, status_code=response.status_code)


def _query_plan(session, sql: str, *, label: str) -> None:
    plan = session.execute(text(f"EXPLAIN QUERY PLAN {sql}")).fetchall()
    print(f"\nQuery plan for {label}:")
    for row in plan:
        print("  ", " | ".join(str(part) for part in row))


def run_sanity_check(positions_target: int, reset: bool) -> None:
    with _app_context() as app:
        session = SessionLocal()
        try:
            if reset:
                session.query(Position).delete()
                session.query(Portfolio).filter(Portfolio.name == PORTFOLIO_NAME).delete()
                session.query(FxRate).filter(FxRate.source == "perf_fixture").delete()
                session.commit()

            currencies = _resolve_currencies(session)
            portfolio = _ensure_portfolio(session, positions_target, currencies)
            _ensure_rates(session, currencies)
            session.commit()

            print(f"Portfolio '{PORTFOLIO_NAME}' ready (id={portfolio.id}).")
            total_positions = (
                session.query(Position).filter(Position.portfolio_id == portfolio.id).count()
            )
            print(f"Positions present: {total_positions}")

            results: list[TimingResult] = []
            with app.test_client() as client:
                endpoints = [
                    ("GET", f"/api/v1/metrics/portfolio/{portfolio.id}/value", "value"),
                    ("GET", f"/api/v1/metrics/portfolio/{portfolio.id}/exposure", "exposure"),
                    ("GET", f"/api/v1/metrics/portfolio/{portfolio.id}/pnl/daily", "daily_pnl"),
                    (
                        "POST",
                        f"/api/v1/metrics/portfolio/{portfolio.id}/whatif",
                        "whatif",
                    ),
                    (
                        "GET",
                        f"/api/v1/metrics/portfolio/{portfolio.id}/value/series?days=30",
                        "value_series",
                    ),
                ]

                payload = {"currency": "EUR", "shock_pct": "1"}

                for method, path, name in endpoints:
                    if method == "POST":
                        start = time.perf_counter()
                        response = client.post(path, json=payload)
                        duration_ms = (time.perf_counter() - start) * 1000
                        results.append(
                            TimingResult(
                                name=name, duration_ms=duration_ms, status_code=response.status_code
                            )
                        )
                    else:
                        results.append(_time_request(client, method, path, name=name))

            print("\nEndpoint timings (ms):")
            for result in results:
                status_mark = (
                    "OK" if 200 <= result.status_code < 300 else f"HTTP {result.status_code}"
                )
                print(f"  {result.name:<15} {result.duration_ms:8.2f}  [{status_mark}]")

            dashboard_ms = sum(result.duration_ms for result in results if result.name != "whatif")
            print(f"\nDashboard bundle (value/exposure/pnl/value_series): {dashboard_ms:.2f} ms")

            value_times = [result.duration_ms for result in results if result.name == "value"]
            if value_times:
                print(
                    f"Value endpoint stats -> min: {min(value_times):.2f} ms | "
                    f"avg: {statistics.mean(value_times):.2f} ms | "
                    f"max: {max(value_times):.2f} ms"
                )

            _query_plan(
                session,
                "SELECT id FROM positions WHERE portfolio_id = ?",
                label="positions lookup (portfolio filter)",
            )
            _query_plan(
                session,
                "SELECT rate FROM fx_rates WHERE base_currency_code = 'USD' ORDER BY timestamp DESC LIMIT 1",
                label="latest rate timestamp",
            )
        finally:
            session.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Performance sanity check helper.")
    parser.add_argument(
        "--positions",
        type=int,
        default=DEFAULT_POSITIONS,
        help=f"Number of positions to seed (default: {DEFAULT_POSITIONS}).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop the existing perf dataset before seeding.",
    )
    args = parser.parse_args()

    random.seed(42)
    run_sanity_check(positions_target=args.positions, reset=args.reset)


if __name__ == "__main__":
    main()
