"""add manufacturing lots tables

Revision ID: 2b9d749fc12f
Revises: 199268f34bba
Create Date: 2026-01-21 14:08:16.411451

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b9d749fc12f'
down_revision: Union[str, Sequence[str], None] = '199268f34bba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # manufacturing_lots table
    op.create_table(
        'manufacturing_lots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lot_number', sa.String(length=128), nullable=False),
        sa.Column('product_code', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('work_order', sa.String(length=128), nullable=True),
        sa.Column('manufacture_date', sa.Date(), nullable=True),
        sa.Column('manufacture_end_date', sa.Date(), nullable=True),
        sa.Column('operator', sa.String(length=255), nullable=True),
        sa.Column('operator_notes', sa.Text(), nullable=True),
        sa.Column('disposition', sa.String(length=32), nullable=True),
        sa.Column('disposition_date', sa.Date(), nullable=True),
        sa.Column('disposition_by_user_id', sa.Integer(), nullable=True),
        sa.Column('disposition_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['disposition_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lot_number')
    )
    op.create_index('idx_manufacturing_lots_lot_number', 'manufacturing_lots', ['lot_number'], unique=False)
    op.create_index('idx_manufacturing_lots_manufacture_date', 'manufacturing_lots', ['manufacture_date'], unique=False)
    op.create_index('idx_manufacturing_lots_product', 'manufacturing_lots', ['product_code'], unique=False)
    op.create_index('idx_manufacturing_lots_status', 'manufacturing_lots', ['status'], unique=False)

    # manufacturing_lot_documents table
    op.create_table(
        'manufacturing_lot_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lot_id', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=128), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=128), nullable=True),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by_user_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['deleted_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lot_id'], ['manufacturing_lots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_manufacturing_lot_docs_lot', 'manufacturing_lot_documents', ['lot_id'], unique=False)
    op.create_index('idx_manufacturing_lot_docs_type', 'manufacturing_lot_documents', ['document_type'], unique=False)
    op.create_index('idx_manufacturing_lot_docs_uploaded_at', 'manufacturing_lot_documents', ['uploaded_at'], unique=False)

    # manufacturing_lot_equipment table
    op.create_table(
        'manufacturing_lot_equipment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lot_id', sa.Integer(), nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=True),
        sa.Column('equipment_name', sa.String(length=255), nullable=True),
        sa.Column('usage_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lot_id'], ['manufacturing_lots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lot_id', 'equipment_id', name='uq_lot_equipment')
    )
    op.create_index('idx_manufacturing_lot_equipment_equipment', 'manufacturing_lot_equipment', ['equipment_id'], unique=False)
    op.create_index('idx_manufacturing_lot_equipment_lot', 'manufacturing_lot_equipment', ['lot_id'], unique=False)

    # manufacturing_lot_materials table
    op.create_table(
        'manufacturing_lot_materials',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('lot_id', sa.Integer(), nullable=False),
        sa.Column('supplier_id', sa.Integer(), nullable=True),
        sa.Column('material_name', sa.String(length=255), nullable=True),
        sa.Column('material_identifier', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.String(length=128), nullable=True),
        sa.Column('lot_number', sa.String(length=128), nullable=True),
        sa.Column('usage_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['lot_id'], ['manufacturing_lots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lot_id', 'material_identifier', name='uq_lot_material')
    )
    op.create_index('idx_manufacturing_lot_materials_lot', 'manufacturing_lot_materials', ['lot_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_manufacturing_lot_materials_lot', table_name='manufacturing_lot_materials')
    op.drop_table('manufacturing_lot_materials')
    op.drop_index('idx_manufacturing_lot_equipment_lot', table_name='manufacturing_lot_equipment')
    op.drop_index('idx_manufacturing_lot_equipment_equipment', table_name='manufacturing_lot_equipment')
    op.drop_table('manufacturing_lot_equipment')
    op.drop_index('idx_manufacturing_lot_docs_uploaded_at', table_name='manufacturing_lot_documents')
    op.drop_index('idx_manufacturing_lot_docs_type', table_name='manufacturing_lot_documents')
    op.drop_index('idx_manufacturing_lot_docs_lot', table_name='manufacturing_lot_documents')
    op.drop_table('manufacturing_lot_documents')
    op.drop_index('idx_manufacturing_lots_status', table_name='manufacturing_lots')
    op.drop_index('idx_manufacturing_lots_product', table_name='manufacturing_lots')
    op.drop_index('idx_manufacturing_lots_manufacture_date', table_name='manufacturing_lots')
    op.drop_index('idx_manufacturing_lots_lot_number', table_name='manufacturing_lots')
    op.drop_table('manufacturing_lots')
