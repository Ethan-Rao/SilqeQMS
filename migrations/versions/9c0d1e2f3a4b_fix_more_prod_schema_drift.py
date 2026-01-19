"""fix more production schema drift (filters_json + shipstation run metrics)

Revision ID: 9c0d1e2f3a4b
Revises: 8b1c2d3e4f50
Create Date: 2026-01-19

Prod drift reported:
- tracing_reports.filters_json missing
- shipstation_sync_runs.synced_count missing (and siblings)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "9c0d1e2f3a4b"
down_revision: Union[str, Sequence[str], None] = "8b1c2d3e4f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, col: sa.Column) -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    if not insp.has_table(table):
        return
    cols = {c["name"] for c in insp.get_columns(table)}
    if col.name not in cols:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(col)


def upgrade() -> None:
    # tracing_reports.filters_json (nullable TEXT)
    _add_column_if_missing("tracing_reports", sa.Column("filters_json", sa.Text(), nullable=True))

    # shipstation_sync_runs run metrics (all nullable for safety)
    _add_column_if_missing("shipstation_sync_runs", sa.Column("synced_count", sa.Integer(), nullable=True))
    _add_column_if_missing("shipstation_sync_runs", sa.Column("skipped_count", sa.Integer(), nullable=True))
    _add_column_if_missing("shipstation_sync_runs", sa.Column("orders_seen", sa.Integer(), nullable=True))
    _add_column_if_missing("shipstation_sync_runs", sa.Column("shipments_seen", sa.Integer(), nullable=True))
    _add_column_if_missing("shipstation_sync_runs", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    _add_column_if_missing("shipstation_sync_runs", sa.Column("message", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("shipstation_sync_runs"):
        cols = {c["name"] for c in insp.get_columns("shipstation_sync_runs")}
        for name in ("message", "duration_seconds", "shipments_seen", "orders_seen", "skipped_count", "synced_count"):
            if name in cols:
                with op.batch_alter_table("shipstation_sync_runs") as batch_op:
                    batch_op.drop_column(name)

    if insp.has_table("tracing_reports"):
        cols = {c["name"] for c in insp.get_columns("tracing_reports")}
        if "filters_json" in cols:
            with op.batch_alter_table("tracing_reports") as batch_op:
                batch_op.drop_column("filters_json")

