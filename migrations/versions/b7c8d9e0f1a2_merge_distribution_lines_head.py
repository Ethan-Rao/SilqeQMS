"""merge heads aa3f4c5d6e7f and 2b9d749fc12f

Revision ID: b7c8d9e0f1a2
Revises: aa3f4c5d6e7f, 2b9d749fc12f
Create Date: 2026-01-28
"""

from typing import Sequence, Union

from alembic import op


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = ("aa3f4c5d6e7f", "2b9d749fc12f")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
