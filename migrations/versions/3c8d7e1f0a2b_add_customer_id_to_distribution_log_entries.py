"""add customer_id fk to distribution_log_entries

Revision ID: 3c8d7e1f0a2b
Revises: 9f2c1a3d4b5c
Create Date: 2026-01-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "3c8d7e1f0a2b"
down_revision: Union[str, Sequence[str], None] = "9f2c1a3d4b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("distribution_log_entries")}

    if "customer_id" not in cols:
        with op.batch_alter_table("distribution_log_entries") as batch_op:
            batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_distribution_log_entries_customer_id",
                "customers",
                ["customer_id"],
                ["id"],
                ondelete="SET NULL",
            )

    # index (idempotent)
    idx_names = {ix.get("name") for ix in insp.get_indexes("distribution_log_entries")}
    if "idx_distribution_log_customer_id" not in idx_names:
        op.create_index("idx_distribution_log_customer_id", "distribution_log_entries", ["customer_id"])


def downgrade() -> None:
    op.drop_index("idx_distribution_log_customer_id", table_name="distribution_log_entries")
    with op.batch_alter_table("distribution_log_entries") as batch_op:
        batch_op.drop_constraint("fk_distribution_log_entries_customer_id", type_="foreignkey")
        batch_op.drop_column("customer_id")

