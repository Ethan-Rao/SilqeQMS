"""Tracker file attachments: payment_entry_attachments + nre_tracker_attachments

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-15 21:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_entry_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("payment_entry_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["payment_entry_id"], ["payment_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_pay_att_entry", "payment_entry_attachments", ["payment_entry_id"])

    op.create_table(
        "nre_tracker_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("nre_entry_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["nre_entry_id"], ["nre_project_entries.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_nre_att_entry", "nre_tracker_attachments", ["nre_entry_id"])


def downgrade() -> None:
    op.drop_index("idx_nre_att_entry", table_name="nre_tracker_attachments")
    op.drop_table("nre_tracker_attachments")
    op.drop_index("idx_pay_att_entry", table_name="payment_entry_attachments")
    op.drop_table("payment_entry_attachments")
