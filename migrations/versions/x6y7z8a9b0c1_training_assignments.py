"""Training assignments (read-and-acknowledge) for Employee Training (Phase 3 Checkpoint 4).

Creates the training_assignments table: an admin assigns a controlled document,
an admin_docs file, or a free-text item to a specific user with an optional due
date; the assignee acknowledges it (acknowledged_at) which writes an audit event.

Revision ID: x6y7z8a9b0c1
Revises: w5x6y7z8a9b0
Create Date: 2026-07-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "x6y7z8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "w5x6y7z8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "training_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_type", sa.String(length=16), nullable=False, server_default="free_text"),
        sa.Column("item_title", sa.String(length=255), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("admin_doc_file_id", sa.Integer(), sa.ForeignKey("admin_doc_files.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("idx_training_assignee", "training_assignments", ["assigned_to_user_id"])
    op.create_index("idx_training_assignee_ack", "training_assignments", ["assigned_to_user_id", "acknowledged_at"])


def downgrade() -> None:
    op.drop_index("idx_training_assignee_ack", table_name="training_assignments")
    op.drop_index("idx_training_assignee", table_name="training_assignments")
    op.drop_table("training_assignments")
