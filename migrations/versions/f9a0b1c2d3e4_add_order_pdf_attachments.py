"""add order_pdf_attachments table

Revision ID: f9a0b1c2d3e4
Revises: e4f5a6b7c8d9
Create Date: 2026-01-22 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_pdf_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sales_order_id", sa.Integer(), nullable=True),
        sa.Column("distribution_entry_id", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("pdf_type", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["distribution_entry_id"], ["distribution_log_entries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_order_pdf_attachments_sales_order_id", "order_pdf_attachments", ["sales_order_id"])
    op.create_index("idx_order_pdf_attachments_distribution_entry_id", "order_pdf_attachments", ["distribution_entry_id"])


def downgrade() -> None:
    op.drop_index("idx_order_pdf_attachments_distribution_entry_id", table_name="order_pdf_attachments")
    op.drop_index("idx_order_pdf_attachments_sales_order_id", table_name="order_pdf_attachments")
    op.drop_table("order_pdf_attachments")
