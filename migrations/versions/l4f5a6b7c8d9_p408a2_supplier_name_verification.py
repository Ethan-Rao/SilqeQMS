"""P4-08A2: purchase_orders.supplier_name + verification_evidence attachment type

Revision ID: l4f5a6b7c8d9
Revises: k3e4f5a6b7c8
Create Date: 2026-08-12 11:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l4f5a6b7c8d9"
down_revision: Union[str, Sequence[str], None] = "k3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("purchase_orders", sa.Column("supplier_name", sa.Text(), nullable=True))
    op.drop_constraint("ck_po_attachments_type", "purchase_order_attachments", type_="check")
    op.create_check_constraint(
        "ck_po_attachments_type",
        "purchase_order_attachments",
        "attachment_type IN ('po_pdf','confirmation_pdf','confirmation_eml','other','verification_evidence')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_po_attachments_type", "purchase_order_attachments", type_="check")
    op.create_check_constraint(
        "ck_po_attachments_type",
        "purchase_order_attachments",
        "attachment_type IN ('po_pdf','confirmation_pdf','confirmation_eml','other')",
    )
    op.drop_column("purchase_orders", "supplier_name")
