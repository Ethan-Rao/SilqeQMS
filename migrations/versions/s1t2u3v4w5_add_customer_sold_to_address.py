"""Add sold_to address fields to customers table.

Stores the billing (Sold To) address from Sales Order PDFs separately
from the physical delivery (Ship To) address which remains in the
existing address1/city/state/zip columns.

Revision ID: s1t2u3v4w5
Revises: r1s2t3u4v5
Create Date: 2026-03-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "s1t2u3v4w5"
down_revision: Union[str, Sequence[str], None] = "r1s2t3u4v5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Sold To (billing) address columns to customers table
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sold_to_address1", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("sold_to_city", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("sold_to_state", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("sold_to_zip", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("customers", schema=None) as batch_op:
        batch_op.drop_column("sold_to_zip")
        batch_op.drop_column("sold_to_state")
        batch_op.drop_column("sold_to_city")
        batch_op.drop_column("sold_to_address1")
