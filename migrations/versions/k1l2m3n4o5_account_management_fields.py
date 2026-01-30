"""Add account management fields and indexes.

Revision ID: k1l2m3n4o5
Revises: j4k5l6m7n8
Create Date: 2026-01-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "j4k5l6m7n8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    cols = {c["name"] for c in insp.get_columns(table)}
    return column in cols


def _has_index(table: str, index_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return False
    return any(i["name"] == index_name for i in insp.get_indexes(table))


def upgrade() -> None:
    if not _has_column("users", "display_name"):
        op.add_column("users", sa.Column("display_name", sa.String(128), nullable=True))
    if not _has_column("audit_events", "client_ip"):
        op.add_column("audit_events", sa.Column("client_ip", sa.String(45), nullable=True))

    if not _has_index("distribution_log_entries", "ix_distribution_log_entries_order_number"):
        op.create_index("ix_distribution_log_entries_order_number", "distribution_log_entries", ["order_number"])
    if not _has_index("distribution_log_entries", "ix_distribution_log_entries_customer_id"):
        op.create_index("ix_distribution_log_entries_customer_id", "distribution_log_entries", ["customer_id"])
    if not _has_index("sales_orders", "ix_sales_orders_order_number"):
        op.create_index("ix_sales_orders_order_number", "sales_orders", ["order_number"])


def downgrade() -> None:
    if _has_index("sales_orders", "ix_sales_orders_order_number"):
        op.drop_index("ix_sales_orders_order_number", table_name="sales_orders")
    if _has_index("distribution_log_entries", "ix_distribution_log_entries_customer_id"):
        op.drop_index("ix_distribution_log_entries_customer_id", table_name="distribution_log_entries")
    if _has_index("distribution_log_entries", "ix_distribution_log_entries_order_number"):
        op.drop_index("ix_distribution_log_entries_order_number", table_name="distribution_log_entries")

    if _has_column("audit_events", "client_ip"):
        op.drop_column("audit_events", "client_ip")
    if _has_column("users", "display_name"):
        op.drop_column("users", "display_name")
