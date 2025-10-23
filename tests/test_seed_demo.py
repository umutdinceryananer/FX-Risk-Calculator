from __future__ import annotations

from app.database import get_session
from app.models import Portfolio, Position
from app.services.demo_seed import PORTFOLIO_NAME, DEMO_POSITIONS, seed_demo_portfolio


def test_seed_demo_portfolio_idempotent(app):
    with app.app_context():
        session = get_session()
        session.query(Position).delete()
        session.query(Portfolio).filter(Portfolio.name == PORTFOLIO_NAME).delete()
        session.commit()

        first_result = seed_demo_portfolio()
        assert first_result.positions_created == len(DEMO_POSITIONS)

        session.expire_all()
        portfolio = session.query(Portfolio).filter(Portfolio.name == PORTFOLIO_NAME).one()
        positions = session.query(Position).filter(Position.portfolio_id == portfolio.id).all()
        assert len(positions) == len(DEMO_POSITIONS)
        snapshot = {(p.currency_code, str(p.amount), p.side) for p in positions}

        second_result = seed_demo_portfolio()
        assert second_result.portfolio_id == first_result.portfolio_id
        assert second_result.positions_created == len(DEMO_POSITIONS)

        session.expire_all()
        positions_again = (
            session.query(Position).filter(Position.portfolio_id == portfolio.id).all()
        )
        assert len(positions_again) == len(DEMO_POSITIONS)
        assert snapshot == {(p.currency_code, str(p.amount), p.side) for p in positions_again}


def test_seed_demo_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-demo"])
    assert result.exit_code == 0
