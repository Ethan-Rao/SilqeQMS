"""P42: nre_invoice_status on sales_orders for NRE Dashboard

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-31 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sales_orders",
        sa.Column(
            "nre_invoice_status",
            sa.String(length=32),
            nullable=False,
            server_default="Pending Invoice",
        ),
    )
    # Historical backfill: order_date before today → 100% Invoiced
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE sales_orders SET nre_invoice_status = '100% Invoiced' "
            "WHERE order_date < CURRENT_DATE"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE sales_orders SET nre_invoice_status = 'Pending Invoice' "
            "WHERE order_date >= CURRENT_DATE"
        )
    )


def downgrade() -> None:
    op.drop_column("sales_orders", "nre_invoice_status")
