"""add base currency to portfolios

Revision ID: a0b5f8d4c5d7
Revises: 8f88ae0c7af8
Create Date: 2025-10-17 19:45:00.000000

"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a0b5f8d4c5d7"
down_revision: str | Sequence[str] | None = "8f88ae0c7af8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.add_column(sa.Column("base_currency_code", sa.String(length=12), nullable=True))

    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE portfolios SET base_currency_code = 'USD' WHERE base_currency_code IS NULL")
    )

    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.alter_column(
            "base_currency_code",
            existing_type=sa.String(length=12),
            nullable=False,
        )
        batch_op.create_foreign_key(
            "fk_portfolios_base_currency",
            "currencies",
            ["base_currency_code"],
            ["code"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.drop_constraint("fk_portfolios_base_currency", type_="foreignkey")
        batch_op.drop_column("base_currency_code")
