"""Add custom_fields JSONB to equipment and suppliers.

Revision ID: i3j4k5l6m7
Revises: h2i3j4k5l6m
Create Date: 2026-01-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i3j4k5l6m7"
down_revision: Union[str, Sequence[str], None] = "h2i3j4k5l6m"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name if bind else ""
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB
        json_type = JSONB
    else:
        json_type = sa.JSON

    op.add_column("equipment", sa.Column("custom_fields", json_type, nullable=True))
    op.add_column("suppliers", sa.Column("custom_fields", json_type, nullable=True))


def downgrade() -> None:
    op.drop_column("suppliers", "custom_fields")
    op.drop_column("equipment", "custom_fields")
