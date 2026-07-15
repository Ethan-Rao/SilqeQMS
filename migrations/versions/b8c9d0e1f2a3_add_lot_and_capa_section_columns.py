"""Add lot quantity/expiration/part_revision and CAPA section dates

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-07-15 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ManufacturingLot — batch metadata from lot logs
    op.add_column("manufacturing_lots", sa.Column("quantity", sa.String(length=128), nullable=True))
    op.add_column("manufacturing_lots", sa.Column("expiration_date", sa.Date(), nullable=True))
    op.add_column("manufacturing_lots", sa.Column("part_revision", sa.String(length=16), nullable=True))

    # CAPARecord — section completion tracking from SILQ CAPA Log
    op.add_column("capa_records", sa.Column("initiated_by", sa.String(length=255), nullable=True))
    op.add_column("capa_records", sa.Column("section_1_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("section_2_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("section_3_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("section_4_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("section_5_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("section_6_date", sa.Date(), nullable=True))
    op.add_column("capa_records", sa.Column("closed_by", sa.String(length=255), nullable=True))
    op.add_column("capa_records", sa.Column("on_time_status", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("capa_records", "on_time_status")
    op.drop_column("capa_records", "closed_by")
    op.drop_column("capa_records", "section_6_date")
    op.drop_column("capa_records", "section_5_date")
    op.drop_column("capa_records", "section_4_date")
    op.drop_column("capa_records", "section_3_date")
    op.drop_column("capa_records", "section_2_date")
    op.drop_column("capa_records", "section_1_date")
    op.drop_column("capa_records", "initiated_by")
    op.drop_column("manufacturing_lots", "part_revision")
    op.drop_column("manufacturing_lots", "expiration_date")
    op.drop_column("manufacturing_lots", "quantity")
