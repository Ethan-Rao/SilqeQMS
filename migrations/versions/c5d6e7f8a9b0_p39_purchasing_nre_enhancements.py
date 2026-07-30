"""P39: payment line items, invoices received, sales order NRE fields

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-30 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_line_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("payment_entry_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["payment_entry_id"], ["payment_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_pay_line_entry", "payment_line_items", ["payment_entry_id"])

    op.create_table(
        "payment_line_item_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("payment_line_item_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["payment_line_item_id"], ["payment_line_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_pay_line_att", "payment_line_item_attachments", ["payment_line_item_id"])

    op.create_table(
        "invoice_received_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("date_received", sa.Date(), nullable=True),
        sa.Column("payee", sa.String(length=256), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "invoice_received_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("invoice_received_entry_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["invoice_received_entry_id"], ["invoice_received_entries.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_inv_recv_att_entry", "invoice_received_attachments", ["invoice_received_entry_id"])

    op.add_column("sales_orders", sa.Column("order_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("sales_orders", sa.Column("invoice_date", sa.Date(), nullable=True))
    op.add_column("sales_orders", sa.Column("po_reference", sa.String(length=128), nullable=True))
    op.add_column("sales_orders", sa.Column("order_description", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "order_description")
    op.drop_column("sales_orders", "po_reference")
    op.drop_column("sales_orders", "invoice_date")
    op.drop_column("sales_orders", "order_amount")
    op.drop_index("idx_inv_recv_att_entry", table_name="invoice_received_attachments")
    op.drop_table("invoice_received_attachments")
    op.drop_table("invoice_received_entries")
    op.drop_index("idx_pay_line_att", table_name="payment_line_item_attachments")
    op.drop_table("payment_line_item_attachments")
    op.drop_index("idx_pay_line_entry", table_name="payment_line_items")
    op.drop_table("payment_line_items")
