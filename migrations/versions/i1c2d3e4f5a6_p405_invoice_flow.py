"""P4-05: invoice flow FKs and disposition on invoice_received_entries

Revision ID: i1c2d3e4f5a6
Revises: h0b1c2d3e4f5
Create Date: 2026-08-11 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "h0b1c2d3e4f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoice_received_entries",
        sa.Column("purchase_order_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "invoice_received_entries",
        sa.Column(
            "disposition",
            sa.String(length=32),
            nullable=False,
            server_default="unassigned",
        ),
    )
    op.create_foreign_key(
        "fk_invoice_received_purchase_order_id",
        "invoice_received_entries",
        "purchase_orders",
        ["purchase_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_invoice_received_purchase_order_id",
        "invoice_received_entries",
        ["purchase_order_id"],
    )
    op.create_check_constraint(
        "ck_invoice_received_disposition",
        "invoice_received_entries",
        "disposition IN ('unassigned','po_matched','other_payment')",
    )

    op.add_column(
        "payment_entries",
        sa.Column("invoice_received_entry_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_payment_entries_invoice_received_entry_id",
        "payment_entries",
        "invoice_received_entries",
        ["invoice_received_entry_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "idx_payment_entries_invoice_received_entry_id",
        "payment_entries",
        ["invoice_received_entry_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_payment_entries_invoice_received_entry_id", table_name="payment_entries")
    op.drop_constraint("fk_payment_entries_invoice_received_entry_id", "payment_entries", type_="foreignkey")
    op.drop_column("payment_entries", "invoice_received_entry_id")

    op.drop_constraint("ck_invoice_received_disposition", "invoice_received_entries", type_="check")
    op.drop_index("idx_invoice_received_purchase_order_id", table_name="invoice_received_entries")
    op.drop_constraint("fk_invoice_received_purchase_order_id", "invoice_received_entries", type_="foreignkey")
    op.drop_column("invoice_received_entries", "disposition")
    op.drop_column("invoice_received_entries", "purchase_order_id")
