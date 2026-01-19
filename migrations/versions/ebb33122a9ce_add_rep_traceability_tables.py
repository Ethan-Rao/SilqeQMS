"""add rep traceability tables

Revision ID: ebb33122a9ce
Revises: 56a470f9ee55
Create Date: 2026-01-15 16:05:22.074339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'ebb33122a9ce'
down_revision: Union[str, Sequence[str], None] = '56a470f9ee55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    insp = inspect(bind)
    existing_tables = set(insp.get_table_names())

    def _has_index(table: str, name: str) -> bool:
        try:
            return any(ix.get("name") == name for ix in insp.get_indexes(table))
        except Exception:
            return False

    if "distribution_log_entries" not in existing_tables:
        op.create_table(
            "distribution_log_entries",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("ship_date", sa.Date(), nullable=False),
            sa.Column("order_number", sa.Text(), nullable=False),
            sa.Column("facility_name", sa.Text(), nullable=False),
            sa.Column("rep_id", sa.Integer(), nullable=True),
            sa.Column("sku", sa.Text(), nullable=False),
            sa.Column("lot_number", sa.Text(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("source", sa.Text(), nullable=False),
            sa.Column("customer_name", sa.Text(), nullable=True),
            sa.Column("rep_name", sa.Text(), nullable=True),
            sa.Column("address1", sa.Text(), nullable=True),
            sa.Column("address2", sa.Text(), nullable=True),
            sa.Column("city", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("zip", sa.Text(), nullable=True),
            sa.Column("country", sa.Text(), nullable=True),
            sa.Column("contact_name", sa.Text(), nullable=True),
            sa.Column("contact_phone", sa.Text(), nullable=True),
            sa.Column("contact_email", sa.Text(), nullable=True),
            sa.Column("tracking_number", sa.Text(), nullable=True),
            sa.Column("ss_shipment_id", sa.Text(), nullable=True),
            sa.Column("evidence_file_storage_key", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["rep_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.CheckConstraint("sku IN ('211810SPT','211610SPT','211410SPT')", name="ck_distribution_log_sku"),
            sa.CheckConstraint("quantity > 0", name="ck_distribution_log_quantity"),
            sa.CheckConstraint(
                "source IN ('shipstation','manual','csv_import','pdf_import')",
                name="ck_distribution_log_source",
            ),
        )
        existing_tables.add("distribution_log_entries")

    # Indexes (idempotent)
    if "distribution_log_entries" in existing_tables:
        for idx_name, cols, unique in (
            ("idx_distribution_log_ship_date", ["ship_date"], False),
            ("idx_distribution_log_source", ["source"], False),
            ("idx_distribution_log_rep_id", ["rep_id"], False),
            ("idx_distribution_log_sku", ["sku"], False),
            ("idx_distribution_log_order_number", ["order_number"], False),
            ("idx_distribution_log_customer_name", ["customer_name"], False),
            ("idx_distribution_log_facility_name", ["facility_name"], False),
            ("uq_distribution_log_ss_shipment_id", ["ss_shipment_id"], True),
        ):
            if not _has_index("distribution_log_entries", idx_name):
                op.create_index(idx_name, "distribution_log_entries", cols, unique=unique)

    if "tracing_reports" not in existing_tables:
        op.create_table(
            "tracing_reports",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("generated_by_user_id", sa.Integer(), nullable=True),
            sa.Column("filters_json", sa.Text(), nullable=False),
            sa.Column("report_storage_key", sa.Text(), nullable=False),
            sa.Column("report_format", sa.String(length=16), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
            sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.CheckConstraint("report_format = 'csv'", name="ck_tracing_reports_format"),
            sa.CheckConstraint("status IN ('draft','final')", name="ck_tracing_reports_status"),
        )
        existing_tables.add("tracing_reports")

    if "tracing_reports" in existing_tables:
        # refresh inspector for indexes if table existed previously
        insp = inspect(op.get_bind())
        if not _has_index("tracing_reports", "idx_tracing_reports_generated_at"):
            op.create_index("idx_tracing_reports_generated_at", "tracing_reports", ["generated_at"])
        if not _has_index("tracing_reports", "idx_tracing_reports_status"):
            op.create_index("idx_tracing_reports_status", "tracing_reports", ["status"])

    if "approvals_eml" not in existing_tables:
        op.create_table(
            "approvals_eml",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("report_id", sa.Integer(), nullable=False),
            sa.Column("storage_key", sa.Text(), nullable=False),
            sa.Column("original_filename", sa.Text(), nullable=False),
            sa.Column("subject", sa.Text(), nullable=True),
            sa.Column("from_email", sa.Text(), nullable=True),
            sa.Column("to_email", sa.Text(), nullable=True),
            sa.Column("email_date", sa.DateTime(timezone=False), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(timezone=False), nullable=False),
            sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["report_id"], ["tracing_reports.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        )
        existing_tables.add("approvals_eml")

    if "approvals_eml" in existing_tables:
        insp = inspect(op.get_bind())
        if not _has_index("approvals_eml", "idx_approvals_eml_report_id"):
            op.create_index("idx_approvals_eml_report_id", "approvals_eml", ["report_id"])
        if not _has_index("approvals_eml", "idx_approvals_eml_uploaded_at"):
            op.create_index("idx_approvals_eml_uploaded_at", "approvals_eml", ["uploaded_at"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_approvals_eml_uploaded_at", table_name="approvals_eml")
    op.drop_index("idx_approvals_eml_report_id", table_name="approvals_eml")
    op.drop_table("approvals_eml")

    op.drop_index("idx_tracing_reports_status", table_name="tracing_reports")
    op.drop_index("idx_tracing_reports_generated_at", table_name="tracing_reports")
    op.drop_table("tracing_reports")

    op.drop_index("uq_distribution_log_ss_shipment_id", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_facility_name", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_customer_name", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_order_number", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_sku", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_rep_id", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_source", table_name="distribution_log_entries")
    op.drop_index("idx_distribution_log_ship_date", table_name="distribution_log_entries")
    op.drop_table("distribution_log_entries")
