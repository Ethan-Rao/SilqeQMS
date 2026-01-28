"""add distribution_lines table and backfill from distribution_log_entries

Revision ID: aa3f4c5d6e7f
Revises: 199268f34bba
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "aa3f4c5d6e7f"
down_revision: Union[str, Sequence[str], None] = "199268f34bba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "distribution_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("distribution_entry_id", sa.Integer(), sa.ForeignKey("distribution_log_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("lot_number", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("sku IN ('211810SPT','211610SPT','211410SPT')", name="ck_distribution_lines_sku"),
        sa.CheckConstraint("quantity > 0", name="ck_distribution_lines_quantity"),
    )
    op.create_index("idx_distribution_lines_entry_id", "distribution_lines", ["distribution_entry_id"])
    op.create_index("idx_distribution_lines_sku", "distribution_lines", ["sku"])

    # Backfill existing distribution_log_entries into distribution_lines
    op.execute(
        """
        INSERT INTO distribution_lines (distribution_entry_id, sku, lot_number, quantity, created_at)
        SELECT id, sku, lot_number, quantity, created_at
        FROM distribution_log_entries
        WHERE sku IS NOT NULL AND lot_number IS NOT NULL AND quantity IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("idx_distribution_lines_sku", table_name="distribution_lines")
    op.drop_index("idx_distribution_lines_entry_id", table_name="distribution_lines")
    op.drop_table("distribution_lines")
