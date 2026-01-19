"""Complete schema drift fix for tracing_reports + shipstation_skipped_orders

Revision ID: a1b2c3d4e5f6
Revises: 9c0d1e2f3a4b
Create Date: 2026-01-19

Production errors:
- tracing_reports.report_storage_key does not exist
- shipstation_skipped_orders.details_json does not exist

This migration adds ALL columns that the models expect but production may be missing.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9c0d1e2f3a4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, col: sa.Column) -> None:
    """Add a column only if the table exists and the column is missing."""
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col.name not in cols:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(col)


def upgrade() -> None:
    # --- tracing_reports: add all potentially missing columns ---
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("report_storage_key", sa.Text(), nullable=True),  # nullable for existing rows
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("report_format", sa.String(16), nullable=True, server_default="csv"),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("status", sa.String(16), nullable=True, server_default="draft"),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("sha256", sa.String(64), nullable=True),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("row_count", sa.Integer(), nullable=True, server_default="0"),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=True),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("generated_at", sa.DateTime(timezone=False), nullable=True),
    )
    _add_column_if_missing(
        "tracing_reports",
        sa.Column("generated_by_user_id", sa.Integer(), nullable=True),
    )

    # --- shipstation_skipped_orders: add all potentially missing columns ---
    _add_column_if_missing(
        "shipstation_skipped_orders",
        sa.Column("details_json", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "shipstation_skipped_orders",
        sa.Column("order_id", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "shipstation_skipped_orders",
        sa.Column("order_number", sa.Text(), nullable=True),
    )
    _add_column_if_missing(
        "shipstation_skipped_orders",
        sa.Column("reason", sa.Text(), nullable=True),  # nullable for migration safety
    )
    _add_column_if_missing(
        "shipstation_skipped_orders",
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=True),
    )

    # --- shipstation_sync_runs: ensure ran_at exists ---
    _add_column_if_missing(
        "shipstation_sync_runs",
        sa.Column("ran_at", sa.DateTime(timezone=False), nullable=True),
    )


def downgrade() -> None:
    # Not safe to drop columns that may contain data; leave them.
    pass
