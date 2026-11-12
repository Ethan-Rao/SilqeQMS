"""Accounting invoices linked to sales orders.

Revision ID: n6o7p8q9r0s1
Revises: m5n6o7p8q9r0
Create Date: 2026-11-12 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n6o7p8q9r0s1"
down_revision: Union[str, Sequence[str], None] = "m5n6o7p8q9r0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_invoice_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sales_order_id", sa.Integer(), nullable=True),
        sa.Column("order_number", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("quote_history_order_total", sa.Numeric(12, 2), nullable=True),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "idx_accounting_invoice_groups_sales_order_id",
        "accounting_invoice_groups",
        ["sales_order_id"],
    )
    op.create_index(
        "uq_accounting_invoice_groups_order_number",
        "accounting_invoice_groups",
        ["order_number"],
        unique=True,
    )
    op.create_table(
        "accounting_invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.Text(), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("invoice_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment", sa.String(length=16), nullable=False),
        sa.Column("open_balance", sa.Numeric(12, 2), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["accounting_invoice_groups.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("invoice_number", name="uq_accounting_invoices_invoice_number"),
    )
    op.create_index("idx_accounting_invoices_group_id", "accounting_invoices", ["group_id"])


def downgrade() -> None:
    op.drop_index("idx_accounting_invoices_group_id", table_name="accounting_invoices")
    op.drop_table("accounting_invoices")
    op.drop_index("uq_accounting_invoice_groups_order_number", table_name="accounting_invoice_groups")
    op.drop_index("idx_accounting_invoice_groups_sales_order_id", table_name="accounting_invoice_groups")
    op.drop_table("accounting_invoice_groups")
