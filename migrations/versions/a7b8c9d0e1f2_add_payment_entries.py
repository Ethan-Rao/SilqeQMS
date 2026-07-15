"""Add payment_entries table and purchase_orders.payment_due_date

Revision ID: a7b8c9d0e1f2
Revises: e5f6a7b8c9d0
Create Date: 2026-07-15 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_entries",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("vendor", sa.String(length=256), nullable=True),
        sa.Column("description", sa.String(length=512), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("payment_due_date", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.add_column("purchase_orders", sa.Column("payment_due_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "payment_due_date")
    op.drop_table("payment_entries")
