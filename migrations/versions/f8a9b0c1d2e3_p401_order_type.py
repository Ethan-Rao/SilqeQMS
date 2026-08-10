"""P4-01: explicit order_type columns on sales_orders

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-08-10 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column("order_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "order_type_is_manual",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "sales_orders",
        sa.Column(
            "order_type_needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("idx_sales_orders_order_type", "sales_orders", ["order_type"])


def downgrade() -> None:
    op.drop_index("idx_sales_orders_order_type", table_name="sales_orders")
    op.drop_column("sales_orders", "order_type_needs_review")
    op.drop_column("sales_orders", "order_type_is_manual")
    op.drop_column("sales_orders", "order_type")
