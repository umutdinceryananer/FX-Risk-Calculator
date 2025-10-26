"""Currency registry that caches valid ISO codes."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.database import get_engine
from app.models import Currency


@dataclass
class CurrencyRegistry:
    """Provides fast lookup for allowed currency codes."""

    codes: set[str] = field(default_factory=set)

    def load(self) -> None:
        """Load currency codes from the database."""

        engine = get_engine()
        try:
            with engine.connect() as connection:
                result = connection.execute(select(Currency.code))
                self.codes = {row[0].upper() for row in result}
        except OperationalError:
            # Migrations may not have created the table yet; fallback to empty set.
            self.codes = set()

    def update(self, items: Iterable[str]) -> None:
        """Merge additional codes into the registry."""

        self.codes.update(code.upper() for code in items)

    def is_allowed(self, code: str) -> bool:
        """Check if the given code is registered."""

        return code.upper() in self.codes


registry = CurrencyRegistry()


def init_registry(app) -> None:
    """Attach the registry to the Flask app and populate codes."""

    registry.load()
    app.extensions["currency_registry"] = registry
