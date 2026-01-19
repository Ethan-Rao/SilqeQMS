"""add shipstation sync tables and distribution external_key

Revision ID: 7f9a1c2d3e4b
Revises: 3c8d7e1f0a2b
Create Date: 2026-01-19

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "7f9a1c2d3e4b"
down_revision: Union[str, Sequence[str], None] = "3c8d7e1f0a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # Distribution Log: add external_key for idempotent ShipStation inserts
    cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}
    if "external_key" not in cols:
        with op.batch_alter_table("distribution_log_entries") as batch_op:
            batch_op.add_column(sa.Column("external_key", sa.Text(), nullable=True))

    idx_names = {ix.get("name") for ix in insp.get_indexes("distribution_log_entries")}
    if "uq_distribution_log_source_external_key" not in idx_names:
        op.create_index(
            "uq_distribution_log_source_external_key",
            "distribution_log_entries",
            ["source", "external_key"],
            unique=True,
        )

    # ShipStation sync run tracking
    if not insp.has_table("shipstation_sync_runs"):
        op.create_table(
            "shipstation_sync_runs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("ran_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("synced_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("skipped_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("orders_seen", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("shipments_seen", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("message", sa.Text(), nullable=True),
        )

    if not insp.has_table("shipstation_skipped_orders"):
        op.create_table(
            "shipstation_skipped_orders",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("order_id", sa.Text(), nullable=True),
            sa.Column("order_number", sa.Text(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("details_json", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("shipstation_skipped_orders"):
        op.drop_table("shipstation_skipped_orders")
    if insp.has_table("shipstation_sync_runs"):
        op.drop_table("shipstation_sync_runs")

    idx_names = {ix.get("name") for ix in insp.get_indexes("distribution_log_entries")}
    if "uq_distribution_log_source_external_key" in idx_names:
        op.drop_index("uq_distribution_log_source_external_key", table_name="distribution_log_entries")

    cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}
    if "external_key" in cols:
        with op.batch_alter_table("distribution_log_entries") as batch_op:
            batch_op.drop_column("external_key")

