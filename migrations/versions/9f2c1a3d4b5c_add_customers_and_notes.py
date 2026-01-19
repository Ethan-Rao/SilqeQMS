"""add customers and customer notes

Revision ID: 9f2c1a3d4b5c
Revises: ebb33122a9ce
Create Date: 2026-01-16

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "9f2c1a3d4b5c"
down_revision: Union[str, Sequence[str], None] = "ebb33122a9ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    existing_tables = set(insp.get_table_names())

    def _has_index(table: str, name: str) -> bool:
        try:
            return any(ix.get("name") == name for ix in insp.get_indexes(table))
        except Exception:
            return False

    if "customers" not in existing_tables:
        op.create_table(
            "customers",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("company_key", sa.Text(), nullable=False),
            sa.Column("facility_name", sa.Text(), nullable=False),
            sa.Column("address1", sa.Text(), nullable=True),
            sa.Column("address2", sa.Text(), nullable=True),
            sa.Column("city", sa.Text(), nullable=True),
            sa.Column("state", sa.Text(), nullable=True),
            sa.Column("zip", sa.Text(), nullable=True),
            sa.Column("contact_name", sa.Text(), nullable=True),
            sa.Column("contact_phone", sa.Text(), nullable=True),
            sa.Column("contact_email", sa.Text(), nullable=True),
            sa.Column("primary_rep_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.ForeignKeyConstraint(["primary_rep_id"], ["users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("company_key", name="uq_customers_company_key"),
        )
        existing_tables.add("customers")

    if "customers" in existing_tables:
        insp = inspect(op.get_bind())
        for idx_name, cols in (
            ("idx_customers_company_key", ["company_key"]),
            ("idx_customers_facility_name", ["facility_name"]),
            ("idx_customers_state", ["state"]),
            ("idx_customers_primary_rep_id", ["primary_rep_id"]),
        ):
            if not _has_index("customers", idx_name):
                op.create_index(idx_name, "customers", cols)

    if "customer_notes" not in existing_tables:
        op.create_table(
            "customer_notes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("customer_id", sa.Integer(), nullable=False),
            sa.Column("note_text", sa.Text(), nullable=False),
            sa.Column("note_date", sa.Date(), nullable=True, server_default=sa.func.current_date()),
            sa.Column("author", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=False),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            ),
            sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        )
        existing_tables.add("customer_notes")

    if "customer_notes" in existing_tables:
        insp = inspect(op.get_bind())
        if not _has_index("customer_notes", "idx_customer_notes_customer_id"):
            op.create_index("idx_customer_notes_customer_id", "customer_notes", ["customer_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_customer_notes_customer_id", table_name="customer_notes")
    op.drop_table("customer_notes")

    op.drop_index("idx_customers_primary_rep_id", table_name="customers")
    op.drop_index("idx_customers_state", table_name="customers")
    op.drop_index("idx_customers_facility_name", table_name="customers")
    op.drop_index("idx_customers_company_key", table_name="customers")
    op.drop_table("customers")

