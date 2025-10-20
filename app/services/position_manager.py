"""Service layer abstraction for managing portfolio positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Union

from sqlalchemy import asc, desc
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.errors import APIError, ValidationError
from app.models import Portfolio, Position, PositionType
from app.validation import validate_currency_code


@dataclass(frozen=True)
class PositionDTO:
    """Immutable representation of a portfolio position."""

    id: int
    portfolio_id: int
    currency_code: str
    amount: Decimal
    side: PositionType
    created_at: datetime


@dataclass(frozen=True)
class PositionCreateData:
    """Validated payload for creating a position."""

    portfolio_id: int
    currency_code: str
    amount: Decimal
    side: Union[PositionType, str] = PositionType.LONG


@dataclass(frozen=True)
class PositionUpdateData:
    """Payload for updating a position."""

    currency_code: Optional[str] = None
    amount: Optional[Decimal] = None
    side: Optional[Union[PositionType, str]] = None


@dataclass(frozen=True)
class PositionListParams:
    """Query parameters for listing positions within a portfolio."""

    portfolio_id: int
    page: int = 1
    page_size: int = 25
    currency: Optional[str] = None
    side: Optional[Union[PositionType, str]] = None
    sort: str = "created_at"
    direction: str = "asc"


@dataclass(frozen=True)
class PositionListResult:
    """Paginated collection data for positions."""

    items: List[PositionDTO]
    total: int
    page: int
    page_size: int


def list_positions(params: PositionListParams) -> PositionListResult:
    """Return paginated positions for the given portfolio."""

    portfolio = _get_portfolio(params.portfolio_id)

    session = get_session()
    query = session.query(Position).filter_by(portfolio_id=portfolio.id)

    if params.currency:
        currency_filter = validate_currency_code(params.currency, field="currency")
        query = query.filter(Position.currency_code == currency_filter)

    normalized_side = _normalize_side(params.side, field="side", allow_none=True)
    if normalized_side is not None:
        query = query.filter(Position.side == normalized_side)

    total = query.count()
    sort_column = _resolve_sort_column(params.sort)
    order_direction = params.direction.lower()
    order_clause = asc(sort_column) if order_direction == "asc" else desc(sort_column)

    offset = (params.page - 1) * params.page_size
    records = (
        query.order_by(order_clause, asc(Position.id))
        .offset(offset)
        .limit(params.page_size)
        .all()
    )

    items = [_to_dto(position) for position in records]
    return PositionListResult(
        items=items,
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


def create_position(data: PositionCreateData) -> PositionDTO:
    """Create a new position under the specified portfolio."""

    portfolio = _get_portfolio(data.portfolio_id)
    session = get_session()

    currency_code = validate_currency_code(data.currency_code, field="currency_code")
    amount = _validate_amount(data.amount)

    side = _normalize_side(data.side, field="side")

    position = Position(
        portfolio_id=portfolio.id,
        currency_code=currency_code,
        amount=amount,
        side=side,
    )
    session.add(position)

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_integrity_error(exc)

    session.refresh(position)
    return _to_dto(position)


def get_position(portfolio_id: int, position_id: int) -> PositionDTO:
    """Fetch a single position belonging to a portfolio."""

    return _to_dto(_get_position(portfolio_id, position_id))


def update_position(portfolio_id: int, position_id: int, data: PositionUpdateData) -> PositionDTO:
    """Update a position belonging to a portfolio."""

    _ = _get_portfolio(portfolio_id)
    session = get_session()
    position = _get_position(portfolio_id, position_id)

    if data.currency_code is not None:
        position.currency_code = validate_currency_code(data.currency_code, field="currency_code")

    if data.amount is not None:
        position.amount = _validate_amount(data.amount)

    if data.side is not None:
        position.side = _normalize_side(data.side, field="side")

    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        _raise_integrity_error(exc)

    session.refresh(position)
    return _to_dto(position)


def delete_position(portfolio_id: int, position_id: int) -> None:
    """Delete a position from the specified portfolio."""

    _ = _get_portfolio(portfolio_id)
    session = get_session()
    position = _get_position(portfolio_id, position_id)
    session.delete(position)
    session.commit()


def _get_portfolio(portfolio_id: int) -> Portfolio:
    session = get_session()
    portfolio = session.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise APIError("Portfolio not found.", status_code=404)
    return portfolio


def _get_position(portfolio_id: int, position_id: int) -> Position:
    session = get_session()
    position = (
        session.query(Position)
        .filter(Position.portfolio_id == portfolio_id, Position.id == position_id)
        .one_or_none()
    )
    if position is None:
        raise APIError("Position not found.", status_code=404)
    return position


def _to_dto(position: Position) -> PositionDTO:
    return PositionDTO(
        id=position.id,
        portfolio_id=position.portfolio_id,
        currency_code=position.currency_code,
        amount=position.amount,
        side=position.side,
        created_at=position.created_at,
    )


def _validate_amount(amount: Decimal) -> Decimal:
    numeric = Decimal(str(amount))
    if numeric <= 0:
        raise ValidationError(
            "Amount must be greater than zero.",
            payload={"field": "amount"},
        )
    return numeric


def _normalize_side(
    value: Optional[Union[PositionType, str]],
    *,
    field: str,
    allow_none: bool = False,
) -> Optional[PositionType]:
    if value is None:
        return None if allow_none else PositionType.LONG

    if isinstance(value, PositionType):
        return value

    normalized = str(value).strip().upper()
    try:
        return PositionType(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"Invalid position side '{value}'.",
            payload={"field": field, "value": value},
        ) from exc


def _raise_integrity_error(exc: IntegrityError) -> None:
    message = str(getattr(exc, "orig", exc))
    raise APIError("Unable to process position request.", status_code=400) from exc


def _resolve_sort_column(value: str):
    normalized = (value or "").strip().lower()
    if normalized == "currency":
        return Position.currency_code
    if normalized == "amount":
        return Position.amount
    if normalized == "side":
        return Position.side
    if normalized == "created_at":
        return Position.created_at
    return Position.created_at
