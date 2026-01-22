"""add_sales_orders_tables

Revision ID: b1c2d3e4f5g6
Revises: 2b9d749fc12f
Create Date: 2026-01-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5g6'
down_revision = '2b9d749fc12f'
branch_labels = None
depends_on = None


def upgrade():
    # Create sales_orders table
    op.create_table(
        'sales_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Order identification
        sa.Column('order_number', sa.Text(), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=False),
        sa.Column('ship_date', sa.Date(), nullable=True),
        
        # Customer (source of truth)
        sa.Column('customer_id', sa.Integer(), nullable=False),
        
        # Source
        sa.Column('source', sa.Text(), nullable=False),
        
        # External references
        sa.Column('ss_order_id', sa.Text(), nullable=True),
        sa.Column('external_key', sa.Text(), nullable=True),
        
        # Optional metadata
        sa.Column('rep_id', sa.Integer(), nullable=True),
        sa.Column('tracking_number', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Status
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('updated_by_user_id', sa.Integer(), nullable=True),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['rep_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        
        # Check constraints
        sa.CheckConstraint("source IN ('shipstation','manual','csv_import','pdf_import')", name='ck_sales_orders_source'),
        sa.CheckConstraint("status IN ('pending','shipped','cancelled','completed')", name='ck_sales_orders_status'),
    )
    
    # Indexes for sales_orders
    op.create_index('idx_sales_orders_customer_id', 'sales_orders', ['customer_id'])
    op.create_index('idx_sales_orders_order_number', 'sales_orders', ['order_number'])
    op.create_index('idx_sales_orders_order_date', 'sales_orders', ['order_date'])
    op.create_index('idx_sales_orders_ship_date', 'sales_orders', ['ship_date'])
    op.create_index('idx_sales_orders_source', 'sales_orders', ['source'])
    op.create_index('idx_sales_orders_status', 'sales_orders', ['status'])
    op.create_index('uq_sales_orders_source_external_key', 'sales_orders', ['source', 'external_key'], unique=True)
    
    # Create sales_order_lines table
    op.create_table(
        'sales_order_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        
        # Link to order
        sa.Column('sales_order_id', sa.Integer(), nullable=False),
        
        # Line item details
        sa.Column('sku', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('lot_number', sa.Text(), nullable=True),
        
        # Line item metadata
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='CASCADE'),
        
        # Check constraints
        sa.CheckConstraint("sku IN ('211810SPT','211610SPT','211410SPT')", name='ck_sales_order_lines_sku'),
        sa.CheckConstraint("quantity > 0", name='ck_sales_order_lines_quantity'),
    )
    
    # Indexes for sales_order_lines
    op.create_index('idx_sales_order_lines_sales_order_id', 'sales_order_lines', ['sales_order_id'])
    op.create_index('idx_sales_order_lines_sku', 'sales_order_lines', ['sku'])
    
    # Add sales_order_id FK to distribution_log_entries
    op.add_column('distribution_log_entries', sa.Column('sales_order_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_distribution_log_entries_sales_order_id',
        'distribution_log_entries',
        'sales_orders',
        ['sales_order_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('idx_distribution_log_sales_order_id', 'distribution_log_entries', ['sales_order_id'])


def downgrade():
    # Drop FK and column from distribution_log_entries
    op.drop_index('idx_distribution_log_sales_order_id', table_name='distribution_log_entries')
    op.drop_constraint('fk_distribution_log_entries_sales_order_id', 'distribution_log_entries', type_='foreignkey')
    op.drop_column('distribution_log_entries', 'sales_order_id')
    
    # Drop sales_order_lines table
    op.drop_index('idx_sales_order_lines_sku', table_name='sales_order_lines')
    op.drop_index('idx_sales_order_lines_sales_order_id', table_name='sales_order_lines')
    op.drop_table('sales_order_lines')
    
    # Drop sales_orders table
    op.drop_index('uq_sales_orders_source_external_key', table_name='sales_orders')
    op.drop_index('idx_sales_orders_status', table_name='sales_orders')
    op.drop_index('idx_sales_orders_source', table_name='sales_orders')
    op.drop_index('idx_sales_orders_ship_date', table_name='sales_orders')
    op.drop_index('idx_sales_orders_order_date', table_name='sales_orders')
    op.drop_index('idx_sales_orders_order_number', table_name='sales_orders')
    op.drop_index('idx_sales_orders_customer_id', table_name='sales_orders')
    op.drop_table('sales_orders')
