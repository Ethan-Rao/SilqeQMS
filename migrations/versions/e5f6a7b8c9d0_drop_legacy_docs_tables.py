"""Drop legacy doc tables (dead code from an earlier phase)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-10 14:30:00.000000

Drops three tables with zero active code references (re-confirmed in Prompt 19):
    quality_docs, training_docs, rep_documents

These predate the eQMS rewrite and are not referenced by any model or blueprint.
Uses IF EXISTS so the migration is safe on environments where they were never
created. downgrade() recreates a minimal shell of each table for reversibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS quality_docs CASCADE")
    op.execute("DROP TABLE IF EXISTS training_docs CASCADE")
    op.execute("DROP TABLE IF EXISTS rep_documents CASCADE")


def downgrade() -> None:
    # Minimal reversible shell (original detailed schema is not retained in code).
    op.create_table(
        "quality_docs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "training_docs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "rep_documents",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
    )
