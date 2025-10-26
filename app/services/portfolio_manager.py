"""Service layer abstraction for portfolio CRUD operations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import asc
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.errors import APIError, ValidationError
from app.models import Portfolio
from app.validation import validate_currency_code


@dataclass(frozen=True)
class PortfolioDTO:
    """Immutable representation of a portfolio record."""

    id: int
    name: str
    base_currency: str


@dataclass(frozen=True)
class PortfolioCreateData:
    """Payload required to create a portfolio."""

    name: str
    base_currency: str


@dataclass(frozen=True)
class PortfolioUpdateData:
    """Payload for partially updating a portfolio."""

    name: str | None = None
    base_currency: str | None = None


@dataclass(frozen=True)
class PortfolioListResult:
    """Paginated collection wrapper for portfolios."""

    items: list[PortfolioDTO]
    total: int
    page: int
    page_size: int


def list_portfolios(*, page: int = 1, page_size: int = 20) -> PortfolioListResult:
    """Return a paginated list of portfolios."""

    session = get_session()
    query = session.query(Portfolio).order_by(asc(Portfolio.id))

    total = query.count()
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    dto_items = [_to_dto(portfolio) for portfolio in items]
    return PortfolioListResult(items=dto_items, total=total, page=page, page_size=page_size)


def create_portfolio(data: PortfolioCreateData) -> PortfolioDTO:
    """Create a new portfolio and return its representation."""

    session = get_session()
    base_currency = validate_currency_code(data.base_currency, field="base_currency")

    normalized_name = _normalize_name(data.name)
    portfolio = Portfolio(
        name=normalized_name,
        base_currency_code=base_currency,
    )
    session.add(portfolio)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_integrity_error(exc)

    session.refresh(portfolio)
    return _to_dto(portfolio)


def get_portfolio(portfolio_id: int) -> PortfolioDTO:
    """Retrieve a single portfolio by its identifier."""

    portfolio = _get_portfolio(portfolio_id)
    return _to_dto(portfolio)


def update_portfolio(portfolio_id: int, data: PortfolioUpdateData) -> PortfolioDTO:
    """Update an existing portfolio and return the updated representation."""

    session = get_session()
    portfolio = _get_portfolio(portfolio_id)

    if data.name is not None:
        portfolio.name = _normalize_name(data.name)

    if data.base_currency is not None:
        portfolio.base_currency_code = validate_currency_code(
            data.base_currency, field="base_currency"
        )

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_integrity_error(exc)

    session.refresh(portfolio)
    return _to_dto(portfolio)


def delete_portfolio(portfolio_id: int) -> None:
    """Delete a portfolio and cascade to its positions."""

    session = get_session()
    portfolio = _get_portfolio(portfolio_id)
    session.delete(portfolio)
    session.commit()


def _get_portfolio(portfolio_id: int) -> Portfolio:
    session = get_session()
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)
    return portfolio


def _to_dto(portfolio: Portfolio) -> PortfolioDTO:
    return PortfolioDTO(
        id=portfolio.id,
        name=portfolio.name,
        base_currency=portfolio.base_currency_code,
    )


def _raise_integrity_error(exc: IntegrityError) -> None:
    message = str(getattr(exc, "orig", exc))
    lowered = message.lower()

    if "portfolios.name" in lowered or "uq_portfolios_name" in lowered:
        raise ValidationError(
            "Portfolio name must be unique.",
            payload={"field": "name"},
        ) from exc

    raise APIError("Unable to process portfolio request.", status_code=400) from exc


def _normalize_name(name: str) -> str:
    normalized = name.strip()
    if not normalized:
        raise ValidationError(
            "Portfolio name cannot be blank.",
            payload={"field": "name"},
        )
    return normalized
