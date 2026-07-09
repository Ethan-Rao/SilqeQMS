"""Records-and-data alignment fields for suppliers, equipment, purchase_orders (Phase 3 Checkpoint 3).

Adds columns so the modules reflect what SILQ actually tracks in the
Equipment Master List, Approved Supplier List (FM6-QM.SLQ015), and PO Log.
All columns are nullable and dialect-agnostic.

Revision ID: w5x6y7z8a9b0
Revises: v4w5x6y7z8a9
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "w5x6y7z8a9b0"
down_revision: Union[str, Sequence[str], None] = "v4w5x6y7z8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Equipment: free-text calibration/PM intervals as recorded on the Master List
    op.add_column("equipment", sa.Column("cal_interval_text", sa.String(length=64), nullable=True))
    op.add_column("equipment", sa.Column("pm_interval_text", sa.String(length=64), nullable=True))

    # Suppliers: certification type + next re-evaluation timing (QM.SLQ015)
    op.add_column("suppliers", sa.Column("certification_type", sa.String(length=128), nullable=True))
    op.add_column("suppliers", sa.Column("next_reevaluation_date", sa.Date(), nullable=True))
    op.create_index("idx_suppliers_next_reevaluation", "suppliers", ["next_reevaluation_date"])

    # Purchase orders: PO Log fields
    op.add_column("purchase_orders", sa.Column("amount", sa.String(length=64), nullable=True))
    op.add_column("purchase_orders", sa.Column("meets_requirements", sa.String(length=16), nullable=True))
    op.add_column("purchase_orders", sa.Column("verified_how", sa.Text(), nullable=True))
    op.add_column("purchase_orders", sa.Column("closed_by", sa.String(length=128), nullable=True))
    op.add_column("purchase_orders", sa.Column("reference", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("purchase_orders", "reference")
    op.drop_column("purchase_orders", "closed_by")
    op.drop_column("purchase_orders", "verified_how")
    op.drop_column("purchase_orders", "meets_requirements")
    op.drop_column("purchase_orders", "amount")

    op.drop_index("idx_suppliers_next_reevaluation", table_name="suppliers")
    op.drop_column("suppliers", "next_reevaluation_date")
    op.drop_column("suppliers", "certification_type")

    op.drop_column("equipment", "pm_interval_text")
    op.drop_column("equipment", "cal_interval_text")
