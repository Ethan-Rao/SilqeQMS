"""Add supplies module tables.

Revision ID: p1q2r3s4t5
Revises: n1o2p3q4r5
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p1q2r3s4t5"
down_revision: Union[str, Sequence[str], None] = "n1o2p3q4r5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_code", sa.String(64), nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="Active"),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("part_number", sa.String(128), nullable=True),
        sa.Column("min_stock_level", sa.Integer(), nullable=True),
        sa.Column("current_stock", sa.Integer(), nullable=True),
        sa.Column("unit_of_measure", sa.String(32), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("custom_fields", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("supply_code"),
    )
    op.create_index("idx_supplies_code", "supplies", ["supply_code"])
    op.create_index("idx_supplies_status", "supplies", ["status"])

    op.create_table(
        "supply_suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("relationship_type", sa.String(128), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["supply_id"], ["supplies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_supply_suppliers_supply", "supply_suppliers", ["supply_id"])
    op.create_index("idx_supply_suppliers_supplier", "supply_suppliers", ["supplier_id"])

    op.create_table(
        "supply_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supply_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False, server_default="application/pdf"),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(64), nullable=False, server_default="general"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.String(512), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["supply_id"], ["supplies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("idx_supply_docs_supply", "supply_documents", ["supply_id"])
    op.create_index("idx_supply_docs_category", "supply_documents", ["category"])


def downgrade() -> None:
    op.drop_index("idx_supply_docs_category", table_name="supply_documents")
    op.drop_index("idx_supply_docs_supply", table_name="supply_documents")
    op.drop_table("supply_documents")
    op.drop_index("idx_supply_suppliers_supplier", table_name="supply_suppliers")
    op.drop_index("idx_supply_suppliers_supply", table_name="supply_suppliers")
    op.drop_table("supply_suppliers")
    op.drop_index("idx_supplies_status", table_name="supplies")
    op.drop_index("idx_supplies_code", table_name="supplies")
    op.drop_table("supplies")
