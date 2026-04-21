"""Add auditor_access_events for temporary auditor files portal.

Revision ID: u3v4w5x6y7z8
Revises: t2u3v4w5x6
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "u3v4w5x6y7z8"
down_revision: Union[str, Sequence[str], None] = "t2u3v4w5x6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auditor_access_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(length=320), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("rel_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_auditor_access_user_created", "auditor_access_events", ["user_id", "created_at"])
    op.create_index("idx_auditor_access_rel_path", "auditor_access_events", ["rel_path"])


def downgrade() -> None:
    op.drop_index("idx_auditor_access_rel_path", table_name="auditor_access_events")
    op.drop_index("idx_auditor_access_user_created", table_name="auditor_access_events")
    op.drop_table("auditor_access_events")
