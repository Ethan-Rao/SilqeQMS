"""Add admin document libraries for placeholder modules.

Revision ID: r1s2t3u4v5
Revises: q1r2s3t4u5
Create Date: 2026-02-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r1s2t3u4v5"
down_revision: Union[str, Sequence[str], None] = "q1r2s3t4u5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_doc_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("library_key", sa.String(64), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["admin_doc_folders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("library_key", "parent_id", "name", name="uq_admin_doc_folder_path"),
    )
    op.create_index("idx_admin_doc_folders_library", "admin_doc_folders", ["library_key"])
    op.create_index("idx_admin_doc_folders_parent", "admin_doc_folders", ["parent_id"])

    op.create_table(
        "admin_doc_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("library_key", sa.String(64), nullable=False),
        sa.Column("folder_id", sa.Integer(), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["folder_id"], ["admin_doc_folders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_admin_doc_files_folder", "admin_doc_files", ["folder_id"])
    op.create_index("idx_admin_doc_files_library", "admin_doc_files", ["library_key"])


def downgrade() -> None:
    op.drop_index("idx_admin_doc_files_library", table_name="admin_doc_files")
    op.drop_index("idx_admin_doc_files_folder", table_name="admin_doc_files")
    op.drop_table("admin_doc_files")
    op.drop_index("idx_admin_doc_folders_parent", table_name="admin_doc_folders")
    op.drop_index("idx_admin_doc_folders_library", table_name="admin_doc_folders")
    op.drop_table("admin_doc_folders")
