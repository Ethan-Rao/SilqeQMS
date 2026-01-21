"""add equipment and suppliers tables

Revision ID: 199268f34bba
Revises: a1b2c3d4e5f6
Create Date: 2026-01-21 13:43:04.663611

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '199268f34bba'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create suppliers, equipment, equipment_suppliers, and managed_documents tables."""
    # Check if tables already exist (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # Create suppliers table
    if "suppliers" not in existing_tables:
        op.create_table(
            "suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(64), nullable=False, server_default="Pending"),
            sa.Column("category", sa.String(128), nullable=True),
            sa.Column("product_service_provided", sa.Text(), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("initial_listing_date", sa.Date(), nullable=True),
            sa.Column("certification_expiration", sa.Date(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("idx_suppliers_name", "suppliers", ["name"])
        op.create_index("idx_suppliers_status", "suppliers", ["status"])
        op.create_index("idx_suppliers_category", "suppliers", ["category"])

    # Create equipment table
    if "equipment" not in existing_tables:
        op.create_table(
            "equipment",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("equip_code", sa.String(64), nullable=False, unique=True),
            sa.Column("status", sa.String(64), nullable=False, server_default="Active"),
            sa.Column("description", sa.String(512), nullable=True),
            sa.Column("mfg", sa.String(255), nullable=True),
            sa.Column("model_no", sa.String(128), nullable=True),
            sa.Column("serial_no", sa.String(128), nullable=True),
            sa.Column("date_in_service", sa.Date(), nullable=True),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("cal_interval", sa.Integer(), nullable=True),
            sa.Column("last_cal_date", sa.Date(), nullable=True),
            sa.Column("cal_due_date", sa.Date(), nullable=True),
            sa.Column("pm_interval", sa.Integer(), nullable=True),
            sa.Column("last_pm_date", sa.Date(), nullable=True),
            sa.Column("pm_due_date", sa.Date(), nullable=True),
            sa.Column("comments", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("updated_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        )
        op.create_index("idx_equipment_code", "equipment", ["equip_code"])
        op.create_index("idx_equipment_status", "equipment", ["status"])
        op.create_index("idx_equipment_location", "equipment", ["location"])
        op.create_index("idx_equipment_cal_due", "equipment", ["cal_due_date"])
        op.create_index("idx_equipment_pm_due", "equipment", ["pm_due_date"])

    # Create equipment_suppliers join table
    if "equipment_suppliers" not in existing_tables:
        op.create_table(
            "equipment_suppliers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("equipment_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("relationship_type", sa.String(128), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.UniqueConstraint("equipment_id", "supplier_id", name="uq_equipment_supplier"),
        )
        op.create_index("idx_equipment_suppliers_equipment", "equipment_suppliers", ["equipment_id"])
        op.create_index("idx_equipment_suppliers_supplier", "equipment_suppliers", ["supplier_id"])

    # Create managed_documents table
    if "managed_documents" not in existing_tables:
        op.create_table(
            "managed_documents",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("entity_type", sa.String(64), nullable=False),
            sa.Column("entity_id", sa.Integer(), nullable=False),
            sa.Column("equipment_id", sa.Integer(), sa.ForeignKey("equipment.id", ondelete="CASCADE"), nullable=True),
            sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=True),
            sa.Column("storage_key", sa.String(512), nullable=False),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(128), nullable=False, server_default="application/octet-stream"),
            sa.Column("sha256", sa.String(64), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("description", sa.String(512), nullable=True),
            sa.Column("document_type", sa.String(128), nullable=True),
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        )
        op.create_index("idx_managed_docs_entity", "managed_documents", ["entity_type", "entity_id"])
        op.create_index("idx_managed_docs_uploaded_at", "managed_documents", ["uploaded_at"])


def downgrade() -> None:
    """Drop tables in reverse order."""
    op.drop_table("managed_documents")
    op.drop_table("equipment_suppliers")
    op.drop_table("equipment")
    op.drop_table("suppliers")
