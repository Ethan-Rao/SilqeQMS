"""P4-06: purchase_orders.is_closed and closed_at (closure separate from status)

Revision ID: j2d3e4f5a6b7
Revises: i1c2d3e4f5a6
Create Date: 2026-08-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "i1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "purchase_orders",
        sa.Column(
            "is_closed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "purchase_orders",
        sa.Column("closed_at", sa.Date(), nullable=True),
    )
    op.create_index("idx_purchase_orders_is_closed", "purchase_orders", ["is_closed"])


def downgrade() -> None:
    op.drop_index("idx_purchase_orders_is_closed", table_name="purchase_orders")
    op.drop_column("purchase_orders", "closed_at")
    op.drop_column("purchase_orders", "is_closed")
