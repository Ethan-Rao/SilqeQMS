"""P4-08A: invoice_received_entries.is_paid

Revision ID: k3e4f5a6b7c8
Revises: j2d3e4f5a6b7
Create Date: 2026-08-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "j2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoice_received_entries",
        sa.Column(
            "is_paid",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index("idx_invoice_received_is_paid", "invoice_received_entries", ["is_paid"])


def downgrade() -> None:
    op.drop_index("idx_invoice_received_is_paid", table_name="invoice_received_entries")
    op.drop_column("invoice_received_entries", "is_paid")
