"""Browse/filter indexes for Document Control at scale (Phase 3 Prompt 5 / E1).

Additive, index-only migration. Supports fast filtering of the ~114 controlled
documents by status and doc type on the list view. No column or data changes;
Postgres-safe and reversible.

Note: idx_documents_category is intentionally NOT created here — it already
exists from ancestor migration v4w5x6y7z8a9 (which added the category column).
Recreating it would fail `alembic upgrade head` with a duplicate-index error.

Revision ID: y7z8a9b0c1d2
Revises: x6y7z8a9b0c1
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op

revision: str = "y7z8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "x6y7z8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_documents_status", "documents", ["status"])
    op.create_index("idx_documents_doc_type", "documents", ["doc_type"])


def downgrade() -> None:
    op.drop_index("idx_documents_doc_type", table_name="documents")
    op.drop_index("idx_documents_status", table_name="documents")
