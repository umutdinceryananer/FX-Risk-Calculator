"""Service layer abstraction for managing portfolio positions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import List, Optional

from app.models import PositionType


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
    side: PositionType


@dataclass(frozen=True)
class PositionUpdateData:
    """Payload for updating a position."""

    currency_code: Optional[str] = None
    amount: Optional[Decimal] = None
    side: Optional[PositionType] = None


@dataclass(frozen=True)
class PositionListParams:
    """Query parameters for listing positions within a portfolio."""

    portfolio_id: int
    page: int = 1
    page_size: int = 25
    currency: Optional[str] = None
    side: Optional[PositionType] = None


@dataclass(frozen=True)
class PositionListResult:
    """Paginated collection data for positions."""

    items: List[PositionDTO]
    total: int
    page: int
    page_size: int


def list_positions(params: PositionListParams) -> PositionListResult:
    """Return paginated positions for the given portfolio."""

    raise NotImplementedError("Position listing has not been implemented yet.")


def create_position(data: PositionCreateData) -> PositionDTO:
    """Create a new position under the specified portfolio."""

    raise NotImplementedError("Position creation has not been implemented yet.")


def get_position(portfolio_id: int, position_id: int) -> PositionDTO:
    """Fetch a single position belonging to a portfolio."""

    raise NotImplementedError("Position retrieval has not been implemented yet.")


def update_position(portfolio_id: int, position_id: int, data: PositionUpdateData) -> PositionDTO:
    """Update a position belonging to a portfolio."""

    raise NotImplementedError("Position updates have not been implemented yet.")


def delete_position(portfolio_id: int, position_id: int) -> None:
    """Delete a position from the specified portfolio."""

    raise NotImplementedError("Position deletion has not been implemented yet.")
