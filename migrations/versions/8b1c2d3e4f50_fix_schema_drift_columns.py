"""fix schema drift: add missing columns expected by code

Revision ID: 8b1c2d3e4f50
Revises: 7f9a1c2d3e4b
Create Date: 2026-01-19

Production drift observed:
- distribution_log_entries.external_key missing
- tracing_reports.generated_by_user_id missing
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "8b1c2d3e4f50"
down_revision: Union[str, Sequence[str], None] = "7f9a1c2d3e4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # distribution_log_entries.external_key + unique index (source, external_key)
    if insp.has_table("distribution_log_entries"):
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

    # tracing_reports.generated_by_user_id (nullable) + FK to users if missing
    if insp.has_table("tracing_reports"):
        cols = {c["name"] for c in insp.get_columns("tracing_reports")}
        if "generated_by_user_id" not in cols:
            with op.batch_alter_table("tracing_reports") as batch_op:
                batch_op.add_column(sa.Column("generated_by_user_id", sa.Integer(), nullable=True))

        # Add FK if not present
        try:
            fks = insp.get_foreign_keys("tracing_reports")
        except Exception:
            fks = []
        fk_names = {fk.get("name") for fk in fks if fk.get("name")}
        if "fk_tracing_reports_generated_by_user_id" not in fk_names:
            with op.batch_alter_table("tracing_reports") as batch_op:
                batch_op.create_foreign_key(
                    "fk_tracing_reports_generated_by_user_id",
                    "users",
                    ["generated_by_user_id"],
                    ["id"],
                    ondelete="SET NULL",
                )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("tracing_reports"):
        try:
            fks = insp.get_foreign_keys("tracing_reports")
        except Exception:
            fks = []
        fk_names = {fk.get("name") for fk in fks if fk.get("name")}
        if "fk_tracing_reports_generated_by_user_id" in fk_names:
            with op.batch_alter_table("tracing_reports") as batch_op:
                batch_op.drop_constraint("fk_tracing_reports_generated_by_user_id", type_="foreignkey")

        cols = {c["name"] for c in insp.get_columns("tracing_reports")}
        if "generated_by_user_id" in cols:
            with op.batch_alter_table("tracing_reports") as batch_op:
                batch_op.drop_column("generated_by_user_id")

    if insp.has_table("distribution_log_entries"):
        idx_names = {ix.get("name") for ix in insp.get_indexes("distribution_log_entries")}
        if "uq_distribution_log_source_external_key" in idx_names:
            op.drop_index("uq_distribution_log_source_external_key", table_name="distribution_log_entries")

        cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}
        if "external_key" in cols:
            with op.batch_alter_table("distribution_log_entries") as batch_op:
                batch_op.drop_column("external_key")

