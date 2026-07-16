"""Add training_type + source_reference to training_assignments and effectiveness_reviews table

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-16 12:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "training_assignments",
        sa.Column("training_type", sa.String(length=32), nullable=False, server_default="read_acknowledge"),
    )
    op.add_column(
        "training_assignments",
        sa.Column("source_reference", sa.String(length=128), nullable=True),
    )

    op.create_table(
        "effectiveness_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("review_year", sa.Integer(), nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_eff_review_user", "effectiveness_reviews", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_eff_review_user", table_name="effectiveness_reviews")
    op.drop_table("effectiveness_reviews")
    op.drop_column("training_assignments", "source_reference")
    op.drop_column("training_assignments", "training_type")
