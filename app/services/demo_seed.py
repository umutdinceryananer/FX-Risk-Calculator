"""Demo data seeding helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, get_session
from app.models import Portfolio, Position, PositionType

PORTFOLIO_NAME = "Global Book (USD)"
PORTFOLIO_BASE_CURRENCY = "USD"

DEMO_POSITIONS = [
    {"currency": "USD", "amount": Decimal("275000.00"), "side": PositionType.LONG},
    {"currency": "EUR", "amount": Decimal("150000.00"), "side": PositionType.LONG},
    {"currency": "GBP", "amount": Decimal("60000.00"), "side": PositionType.SHORT},
    {"currency": "JPY", "amount": Decimal("12500000.00"), "side": PositionType.LONG},
    {"currency": "TRY", "amount": Decimal("500000.00"), "side": PositionType.SHORT},
    {"currency": "CHF", "amount": Decimal("45000.00"), "side": PositionType.LONG},
]


@dataclass(frozen=True)
class SeedResult:
    portfolio_id: int
    positions_created: int
    created: bool


def seed_demo_portfolio() -> SeedResult:
    """Create or refresh the demo portfolio with deterministic positions."""

    session = get_session()
    created = False
    try:
        portfolio = session.query(Portfolio).filter(Portfolio.name == PORTFOLIO_NAME).one_or_none()
        if portfolio is None:
            portfolio = Portfolio(name=PORTFOLIO_NAME, base_currency_code=PORTFOLIO_BASE_CURRENCY)
            session.add(portfolio)
            session.flush()
            created = True
        else:
            if portfolio.base_currency_code != PORTFOLIO_BASE_CURRENCY:
                portfolio.base_currency_code = PORTFOLIO_BASE_CURRENCY

        session.query(Position).filter(Position.portfolio_id == portfolio.id).delete()
        session.flush()

        positions: list[Position] = [
            Position(
                portfolio_id=portfolio.id,
                currency_code=entry["currency"],
                amount=entry["amount"],
                side=entry["side"],
            )
            for entry in DEMO_POSITIONS
        ]
        session.add_all(positions)
        session.commit()
        return SeedResult(
            portfolio_id=portfolio.id,
            positions_created=len(positions),
            created=created,
        )
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        SessionLocal.remove()
