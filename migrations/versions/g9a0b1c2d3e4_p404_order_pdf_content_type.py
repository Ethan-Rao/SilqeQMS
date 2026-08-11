"""P4-04: content_type and size_bytes on order_pdf_attachments

Revision ID: g9a0b1c2d3e4
Revises: f8a9b0c1d2e3
Create Date: 2026-08-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "order_pdf_attachments",
        sa.Column("content_type", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "order_pdf_attachments",
        sa.Column("size_bytes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("order_pdf_attachments", "size_bytes")
    op.drop_column("order_pdf_attachments", "content_type")
