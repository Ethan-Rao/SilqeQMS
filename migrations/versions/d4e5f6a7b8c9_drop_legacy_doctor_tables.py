"""Drop legacy doctor tables (dead code from an earlier phase)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-10 10:45:00.000000

Drops three tables with zero active code references (confirmed in Prompt 18):
    doctor_billing_data, hospital_doctor_affiliations, doctors

These predate the eQMS rewrite and are not referenced by any model or blueprint.
Uses IF EXISTS so the migration is safe on environments where they were never
created. downgrade() recreates a minimal shell of each table for reversibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop dependents first, then the parent. CASCADE covers any FKs we don't model.
    op.execute("DROP TABLE IF EXISTS doctor_billing_data CASCADE")
    op.execute("DROP TABLE IF EXISTS hospital_doctor_affiliations CASCADE")
    op.execute("DROP TABLE IF EXISTS doctors CASCADE")


def downgrade() -> None:
    # Minimal reversible shell (original detailed schema is not retained in code).
    op.create_table(
        "doctors",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "doctor_billing_data",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=True),
    )
    op.create_table(
        "hospital_doctor_affiliations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=True),
    )
