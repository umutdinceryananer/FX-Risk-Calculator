"""seed currencies

Revision ID: 8f88ae0c7af8
Revises: bb44eae4a137
Create Date: 2025-10-14 19:34:46.848806

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

currencies_table = sa.table(
    "currencies",
    sa.column("code", sa.String(length=12)),
    sa.column("name", sa.String(length=120)),
)


# revision identifiers, used by Alembic.
revision: str = '8f88ae0c7af8'
down_revision: Union[str, Sequence[str], None] = 'bb44eae4a137'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    currencies = [
        {"code": "USD", "name": "United States Dollar"},
        {"code": "EUR", "name": "Euro"},
        {"code": "GBP", "name": "British Pound Sterling"},
        {"code": "JPY", "name": "Japanese Yen"},
        {"code": "TRY", "name": "Turkish Lira"},
        {"code": "CHF", "name": "Swiss Franc"},
        {"code": "AUD", "name": "Australian Dollar"},
        {"code": "CAD", "name": "Canadian Dollar"},
        {"code": "NZD", "name": "New Zealand Dollar"},
        {"code": "SEK", "name": "Swedish Krona"},
        {"code": "NOK", "name": "Norwegian Krone"},
        {"code": "DKK", "name": "Danish Krone"},
        {"code": "CNY", "name": "Chinese Yuan"},
        {"code": "HKD", "name": "Hong Kong Dollar"},
        {"code": "SGD", "name": "Singapore Dollar"},
        {"code": "INR", "name": "Indian Rupee"},
        {"code": "ZAR", "name": "South African Rand"},
        {"code": "BRL", "name": "Brazilian Real"},
        {"code": "MXN", "name": "Mexican Peso"},
        {"code": "KRW", "name": "South Korean Won"},
    ]

    op.bulk_insert(currencies_table, currencies)


def downgrade() -> None:
    """Downgrade schema."""
    codes = [
        "USD", "EUR", "GBP", "JPY", "TRY", "CHF", "AUD", "CAD", "NZD", "SEK",
        "NOK", "DKK", "CNY", "HKD", "SGD", "INR", "ZAR", "BRL", "MXN", "KRW",
    ]
    delete_statement = currencies_table.delete().where(
        currencies_table.c.code.in_(codes)
    )
    op.execute(delete_statement)
