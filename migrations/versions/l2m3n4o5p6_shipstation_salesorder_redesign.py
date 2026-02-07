"""Add customer_code and relax sales_order_lines sku constraint.

Revision ID: l2m3n4o5p6
Revises: g1h2i3j4k5l6
Create Date: 2026-02-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("customer_code", sa.Text(), nullable=True))
    op.create_index("idx_customers_customer_code", "customers", ["customer_code"])
    op.drop_constraint("ck_sales_order_lines_sku", "sales_order_lines", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "ck_sales_order_lines_sku",
        "sales_order_lines",
        "sku IN ('211810SPT','211610SPT','211410SPT')",
    )
    op.drop_index("idx_customers_customer_code", table_name="customers")
    op.drop_column("customers", "customer_code")
