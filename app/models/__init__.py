"""SQLAlchemy ORM models for core FX risk entities."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, desc, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Currency(Base):
    """Represents a tradable currency."""

    __tablename__ = "currencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Currency code={self.code}>"


class Portfolio(Base):
    """Collection of positions managed together."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )

    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="portfolio", cascade="all, delete-orphan"
    )
    base_currency: Mapped["Currency"] = relationship(
        "Currency", foreign_keys=[base_currency_code]
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Portfolio name={self.name} base={self.base_currency_code}>"


class FxRate(Base):
    """Foreign exchange rate snapshot between two currencies."""

    __tablename__ = "fx_rates"
    __table_args__ = (
        UniqueConstraint(
            "base_currency_code",
            "target_currency_code",
            "timestamp",
            "source",
            name="uq_fx_rates_unique_rate",
        ),
        Index(
            "ix_fx_rates_pair_timestamp_desc",
            "base_currency_code",
            "target_currency_code",
            desc("timestamp"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    base_currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )
    target_currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)

    base_currency: Mapped["Currency"] = relationship(
        "Currency", foreign_keys=[base_currency_code], lazy="joined"
    )
    target_currency: Mapped["Currency"] = relationship(
        "Currency", foreign_keys=[target_currency_code], lazy="joined"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<FxRate {self.base_currency_code}->{self.target_currency_code} "
            f"{self.timestamp.isoformat()} rate={self.rate}>"
        )


class PositionType(str, Enum):
    """Side indicator for a position."""

    LONG = "LONG"
    SHORT = "SHORT"


class Position(Base):
    """Represents holdings in a particular currency for a portfolio."""

    __tablename__ = "positions"
    __table_args__ = (
        Index("ix_positions_portfolio_currency", "portfolio_id", "currency_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    currency_code: Mapped[str] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    side: Mapped[PositionType] = mapped_column(
        SqlEnum(PositionType, name="position_type"),
        nullable=False,
        default=PositionType.LONG,
        server_default=PositionType.LONG.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    portfolio: Mapped["Portfolio"] = relationship("Portfolio", back_populates="positions")
    currency: Mapped["Currency"] = relationship("Currency")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Position portfolio={self.portfolio_id} currency={self.currency_code} amount={self.amount} side={self.side}>"
        )
