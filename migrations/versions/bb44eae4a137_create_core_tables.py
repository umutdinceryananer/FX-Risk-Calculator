"""create core tables

Revision ID: bb44eae4a137
Revises: 
Create Date: 2025-10-14 19:27:04.590232

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb44eae4a137'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "currencies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=12), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("base_currency_code", sa.String(length=12), nullable=False),
        sa.Column("target_currency_code", sa.String(length=12), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rate", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_currency_code"], ["currencies.code"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_currency_code"], ["currencies.code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "base_currency_code",
            "target_currency_code",
            "timestamp",
            "source",
            name="uq_fx_rates_unique_rate",
        ),
    )
    op.create_index(
        "ix_fx_rates_pair_timestamp_desc",
        "fx_rates",
        [
            sa.column("base_currency_code"),
            sa.column("target_currency_code"),
            sa.text("timestamp DESC"),
        ],
    )
    op.create_table(
        "positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=12), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"], ["currencies.code"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("positions", schema=None) as batch_op:
        batch_op.create_index(
            "ix_positions_portfolio_currency",
            ["portfolio_id", "currency_code"],
            unique=False,
        )

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("positions", schema=None) as batch_op:
        batch_op.drop_index("ix_positions_portfolio_currency")

    op.drop_table("positions")
    op.drop_index("ix_fx_rates_pair_timestamp_desc", table_name="fx_rates")
    op.drop_table("fx_rates")
    op.drop_table("portfolios")
    op.drop_table("currencies")
