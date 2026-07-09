"""Add category column to documents for subsystem browsing (Phase 3 P1.3).

Revision ID: v4w5x6y7z8a9
Revises: u3v4w5x6y7z8
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "v4w5x6y7z8a9"
down_revision: Union[str, Sequence[str], None] = "u3v4w5x6y7z8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("category", sa.String(length=64), nullable=True))
    op.create_index("idx_documents_category", "documents", ["category"])


def downgrade() -> None:
    op.drop_index("idx_documents_category", table_name="documents")
    op.drop_column("documents", "category")
