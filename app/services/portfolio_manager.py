"""Service layer abstraction for portfolio CRUD operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


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

    name: Optional[str] = None
    base_currency: Optional[str] = None


@dataclass(frozen=True)
class PortfolioListResult:
    """Paginated collection wrapper for portfolios."""

    items: List[PortfolioDTO]
    total: int
    page: int
    page_size: int


def list_portfolios(*, page: int = 1, page_size: int = 20) -> PortfolioListResult:
    """Return a paginated list of portfolios.

    Args:
        page: The 1-based page index.
        page_size: Number of records to include per page.

    Raises:
        NotImplementedError: Until the persistence logic is implemented.
    """

    raise NotImplementedError("Portfolio listing has not been implemented yet.")


def create_portfolio(data: PortfolioCreateData) -> PortfolioDTO:
    """Create a new portfolio and return its representation.

    Args:
        data: Validated creation payload.

    Raises:
        NotImplementedError: Until the persistence logic is implemented.
    """

    raise NotImplementedError("Portfolio creation has not been implemented yet.")


def get_portfolio(portfolio_id: int) -> PortfolioDTO:
    """Retrieve a single portfolio by its identifier.

    Args:
        portfolio_id: Unique identifier of the portfolio.

    Raises:
        NotImplementedError: Until the persistence logic is implemented.
    """

    raise NotImplementedError("Portfolio retrieval has not been implemented yet.")


def update_portfolio(portfolio_id: int, data: PortfolioUpdateData) -> PortfolioDTO:
    """Update an existing portfolio and return the updated representation.

    Args:
        portfolio_id: Unique identifier of the portfolio to update.
        data: Partial update payload.

    Raises:
        NotImplementedError: Until the persistence logic is implemented.
    """

    raise NotImplementedError("Portfolio updates have not been implemented yet.")


def delete_portfolio(portfolio_id: int) -> None:
    """Delete a portfolio and cascade to its positions.

    Args:
        portfolio_id: Unique identifier of the portfolio to delete.

    Raises:
        NotImplementedError: Until the persistence logic is implemented.
    """

    raise NotImplementedError("Portfolio deletion has not been implemented yet.")

