"""merge heads b1c2d3e4f5g6 and c8f1b2a3d4e5

Revision ID: d1e2f3a4b5c6
Revises: b1c2d3e4f5g6, c8f1b2a3d4e5
Create Date: 2026-01-22 10:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = ("b1c2d3e4f5g6", "c8f1b2a3d4e5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
