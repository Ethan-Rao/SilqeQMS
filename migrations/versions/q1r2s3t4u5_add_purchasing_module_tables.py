"""Add purchasing module tables.

Revision ID: q1r2s3t4u5
Revises: p1q2r3s4t5
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "q1r2s3t4u5"
down_revision: Union[str, Sequence[str], None] = "p1q2r3s4t5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("po_number", sa.String(64), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("po_number"),
        sa.CheckConstraint(
            "status IN ('pending','received','partial','cancelled')",
            name="ck_purchase_orders_status",
        ),
    )
    op.create_index("idx_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("idx_purchase_orders_po_number", "purchase_orders", ["po_number"])
    op.create_index("idx_purchase_orders_order_date", "purchase_orders", ["order_date"])

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("item_code", sa.String(128), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.String(32), nullable=True),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_po_lines_purchase_order_id", "purchase_order_lines", ["purchase_order_id"])

    op.create_table(
        "purchase_order_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_order_id", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(32), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "attachment_type IN ('po_pdf','confirmation_pdf','confirmation_eml','other')",
            name="ck_po_attachments_type",
        ),
    )
    op.create_index("idx_po_attachments_purchase_order_id", "purchase_order_attachments", ["purchase_order_id"])


def downgrade() -> None:
    op.drop_index("idx_po_attachments_purchase_order_id", table_name="purchase_order_attachments")
    op.drop_table("purchase_order_attachments")
    op.drop_index("idx_po_lines_purchase_order_id", table_name="purchase_order_lines")
    op.drop_table("purchase_order_lines")
    op.drop_index("idx_purchase_orders_order_date", table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_po_number", table_name="purchase_orders")
    op.drop_index("idx_purchase_orders_supplier_id", table_name="purchase_orders")
    op.drop_table("purchase_orders")
