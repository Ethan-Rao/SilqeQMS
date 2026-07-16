"""Add customer_type on customers and nre_project_entries table

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-15 17:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("customer_type", sa.Text(), nullable=False, server_default="auto"),
    )
    op.create_table(
        "nre_project_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("sales_order_id", sa.Integer(), nullable=False),
        sa.Column("invoice_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("expected_invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_status", sa.String(length=32), nullable=False, server_default="Pending Invoice"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("sales_order_id", name="uq_nre_project_entries_sales_order_id"),
    )
    op.create_index("idx_nre_entries_order", "nre_project_entries", ["sales_order_id"])


def downgrade() -> None:
    op.drop_index("idx_nre_entries_order", table_name="nre_project_entries")
    op.drop_table("nre_project_entries")
    op.drop_column("customers", "customer_type")
