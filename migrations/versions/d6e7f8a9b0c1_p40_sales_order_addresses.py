"""P40: per-order Sold To / Ship To address columns on sales_orders

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sales_orders", sa.Column("sold_to_address1", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("sold_to_city", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("sold_to_state", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("sold_to_zip", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_name", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_address1", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_city", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_state", sa.Text(), nullable=True))
    op.add_column("sales_orders", sa.Column("ship_to_zip", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sales_orders", "ship_to_zip")
    op.drop_column("sales_orders", "ship_to_state")
    op.drop_column("sales_orders", "ship_to_city")
    op.drop_column("sales_orders", "ship_to_address1")
    op.drop_column("sales_orders", "ship_to_name")
    op.drop_column("sales_orders", "sold_to_zip")
    op.drop_column("sales_orders", "sold_to_state")
    op.drop_column("sales_orders", "sold_to_city")
    op.drop_column("sales_orders", "sold_to_address1")
