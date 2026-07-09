"""Widen document_revisions change_summary to Text

Revision ID: 9494e9789a92
Revises: z8a9b0c1d2e3
Create Date: 2026-07-09 11:36:51.492920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9494e9789a92'
down_revision: Union[str, Sequence[str], None] = 'z8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "document_revisions",
        "change_summary",
        type_=sa.Text(),
        existing_type=sa.String(length=512),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "document_revisions",
        "change_summary",
        type_=sa.String(length=512),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
