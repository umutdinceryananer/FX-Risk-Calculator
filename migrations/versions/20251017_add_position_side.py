"""add position side enum

Revision ID: b1d6f2c3e9a4
Revises: a0b5f8d4c5d7
Create Date: 2025-10-17 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1d6f2c3e9a4"
down_revision: Union[str, Sequence[str], None] = "a0b5f8d4c5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    position_type_enum = sa.Enum("LONG", "SHORT", name="position_type")
    position_type_enum.create(op.get_bind(), checkfirst=True)

    with op.batch_alter_table("positions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "side",
                position_type_enum,
                nullable=True,
                server_default="LONG",
            )
        )

    op.execute(
        sa.text(
            "UPDATE positions SET side = :default_value WHERE side IS NULL"
        ).bindparams(default_value="LONG")
    )

    with op.batch_alter_table("positions", schema=None) as batch_op:
        batch_op.alter_column("side", nullable=False, server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("positions", schema=None) as batch_op:
        batch_op.drop_column("side")

    position_type_enum = sa.Enum("LONG", "SHORT", name="position_type")
    position_type_enum.drop(op.get_bind(), checkfirst=True)
