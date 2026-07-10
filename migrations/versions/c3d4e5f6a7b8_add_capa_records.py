"""Add capa_records table

Revision ID: c3d4e5f6a7b8
Revises: f1a2b3c4d5e6
Create Date: 2026-07-09 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capa_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("capa_number", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("opened_date", sa.Date(), nullable=True),
        sa.Column("target_close_date", sa.Date(), nullable=True),
        sa.Column("closed_date", sa.Date(), nullable=True),
        sa.Column("root_cause_category", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("corrective_actions", sa.Text(), nullable=True),
        sa.Column("effectiveness_check_date", sa.Date(), nullable=True),
        sa.Column("effectiveness_result", sa.Text(), nullable=True),
        sa.Column("linked_doc_number", sa.String(length=64), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("capa_number", name="uq_capa_records_number"),
    )
    op.create_index("idx_capa_records_status", "capa_records", ["status"])
    op.create_index("idx_capa_records_number", "capa_records", ["capa_number"])


def downgrade() -> None:
    op.drop_index("idx_capa_records_number", table_name="capa_records")
    op.drop_index("idx_capa_records_status", table_name="capa_records")
    op.drop_table("capa_records")
