"""Shared datetime helpers for enforcing UTC awareness."""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    """Return a timezone-aware datetime in UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def utc_now() -> datetime:
    """Return the current UTC datetime."""

    return datetime.now(UTC)

