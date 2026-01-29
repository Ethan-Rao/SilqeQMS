"""Add supplier contact fields and managed document extracted text.

Revision ID: j4k5l6m7n8
Revises: i3j4k5l6m7
Create Date: 2026-01-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j4k5l6m7n8"
down_revision: Union[str, Sequence[str], None] = "i3j4k5l6m7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("suppliers", sa.Column("contact_name", sa.String(255), nullable=True))
    op.add_column("suppliers", sa.Column("contact_email", sa.String(255), nullable=True))
    op.add_column("suppliers", sa.Column("contact_phone", sa.String(64), nullable=True))

    op.add_column("managed_documents", sa.Column("extracted_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("managed_documents", "extracted_text")

    op.drop_column("suppliers", "contact_phone")
    op.drop_column("suppliers", "contact_email")
    op.drop_column("suppliers", "contact_name")
