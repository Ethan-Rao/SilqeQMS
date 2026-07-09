"""Add nullable document_revision_id to training_assignments (Phase 3 Prompt 8 / E3).

Lets a training assignment target a specific controlled-document revision (e.g.
"acknowledge QM.SLQ016 Rev D") so a stale acknowledgement is obvious when a newer
revision becomes current. Additive + nullable with ON DELETE SET NULL, so existing
rows are unaffected. Single head.

Revision ID: z8a9b0c1d2e3
Revises: y7z8a9b0c1d2
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "z8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "y7z8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "training_assignments",
        sa.Column(
            "document_revision_id",
            sa.Integer(),
            sa.ForeignKey("document_revisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("training_assignments", "document_revision_id")
