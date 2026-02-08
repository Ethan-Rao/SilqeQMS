"""Add document categories and primary flags.

Revision ID: n1o2p3q4r5
Revises: l2m3n4o5p6
Create Date: 2026-02-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "n1o2p3q4r5"
down_revision: Union[str, Sequence[str], None] = "l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "managed_documents",
        sa.Column("category", sa.String(64), nullable=True, server_default="general"),
    )
    op.add_column(
        "managed_documents",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("idx_managed_docs_category", "managed_documents", ["category"])


def downgrade() -> None:
    op.drop_index("idx_managed_docs_category", table_name="managed_documents")
    op.drop_column("managed_documents", "is_primary")
    op.drop_column("managed_documents", "category")
