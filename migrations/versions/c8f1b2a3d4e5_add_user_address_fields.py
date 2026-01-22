"""add user address fields

Revision ID: c8f1b2a3d4e5
Revises: 2b9d749fc12f
Create Date: 2026-01-22 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8f1b2a3d4e5'
down_revision: Union[str, Sequence[str], None] = '2b9d749fc12f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('address1', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('address2', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('state', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('zip', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'zip')
    op.drop_column('users', 'state')
    op.drop_column('users', 'city')
    op.drop_column('users', 'address2')
    op.drop_column('users', 'address1')
