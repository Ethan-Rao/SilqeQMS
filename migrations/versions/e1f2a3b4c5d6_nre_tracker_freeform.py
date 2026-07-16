"""NRE tracker free-form: nullable sales_order_id + ledger columns

Revision ID: e1f2a3b4c5d6
Revises: c9d0e1f2a3b4
Create Date: 2026-07-15 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_nre_project_entries_sales_order_id", "nre_project_entries", type_="unique")
    op.alter_column("nre_project_entries", "sales_order_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("nre_project_entries", sa.Column("entry_date", sa.Date(), nullable=True))
    op.add_column("nre_project_entries", sa.Column("customer_name", sa.Text(), nullable=True))
    op.add_column("nre_project_entries", sa.Column("order_ref", sa.Text(), nullable=True))
    op.add_column("nre_project_entries", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("nre_project_entries", "description")
    op.drop_column("nre_project_entries", "order_ref")
    op.drop_column("nre_project_entries", "customer_name")
    op.drop_column("nre_project_entries", "entry_date")
    op.alter_column("nre_project_entries", "sales_order_id", existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint("uq_nre_project_entries_sales_order_id", "nre_project_entries", ["sales_order_id"])
