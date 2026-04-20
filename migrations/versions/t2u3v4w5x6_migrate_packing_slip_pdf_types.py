"""Migrate packing slip pdf_type values to canonical packing_slip.

Revision ID: t2u3v4w5x6
Revises: s1t2u3v4w5
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op


revision: str = "t2u3v4w5x6"
down_revision: Union[str, Sequence[str], None] = "s1t2u3v4w5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE order_pdf_attachments
        SET pdf_type = 'packing_slip'
        WHERE pdf_type IN ('shipping_label', 'delivery_verification')
        """
    )


def downgrade() -> None:
    # Cannot distinguish original values; restore bulk path to legacy name.
    op.execute(
        """
        UPDATE order_pdf_attachments
        SET pdf_type = 'shipping_label'
        WHERE pdf_type = 'packing_slip'
        """
    )
