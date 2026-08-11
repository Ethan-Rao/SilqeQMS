"""P4-04B: customers.is_distributor flag

Revision ID: h0b1c2d3e4f5
Revises: g9a0b1c2d3e4
Create Date: 2026-08-11 10:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h0b1c2d3e4f5"
down_revision: Union[str, Sequence[str], None] = "g9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column(
            "is_distributor",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("customers", "is_distributor")
