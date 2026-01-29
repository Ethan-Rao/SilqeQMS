"""Create reps table and update rep foreign keys.

Revision ID: h2i3j4k5l6m
Revises: g1h2i3j4k5l6
Create Date: 2026-01-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h2i3j4k5l6m"
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("reps"):
        op.create_table(
            "reps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("email", sa.Text(), nullable=True),
            sa.Column("phone", sa.Text(), nullable=True),
            sa.Column("territory", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")),
        )
    else:
        existing_columns = {col["name"] for col in insp.get_columns("reps")}
        if "is_active" not in existing_columns:
            op.add_column("reps", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")))
        if "phone" not in existing_columns:
            op.add_column("reps", sa.Column("phone", sa.Text(), nullable=True))
        if "territory" not in existing_columns:
            op.add_column("reps", sa.Column("territory", sa.Text(), nullable=True))
        if "created_at" not in existing_columns:
            op.add_column("reps", sa.Column("created_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")))
        if "updated_at" not in existing_columns:
            op.add_column("reps", sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False, server_default=sa.text("NOW()")))

    # Ensure index exists
    existing_indexes = {idx["name"] for idx in insp.get_indexes("reps")} if insp.has_table("reps") else set()
    if "idx_reps_name" not in existing_indexes:
        op.create_index("idx_reps_name", "reps", ["name"])

    # Seed reps from users referenced by rep assignments.
    op.execute(
        """
        INSERT INTO reps (id, name, email, is_active, created_at, updated_at)
        SELECT DISTINCT u.id, u.email, u.email, u.is_active, NOW(), NOW()
        FROM users u
        WHERE u.id IN (
            SELECT DISTINCT primary_rep_id FROM customers WHERE primary_rep_id IS NOT NULL
            UNION
            SELECT DISTINCT rep_id FROM customer_reps WHERE rep_id IS NOT NULL
            UNION
            SELECT DISTINCT rep_id FROM distribution_log_entries WHERE rep_id IS NOT NULL
        )
        ON CONFLICT (id) DO NOTHING
        """
    )

    # Repoint foreign keys to reps (Postgres-safe).
    op.execute("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_primary_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE customers
          ADD CONSTRAINT customers_primary_rep_id_fkey
          FOREIGN KEY (primary_rep_id) REFERENCES reps (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )

    op.execute("ALTER TABLE customer_reps DROP CONSTRAINT IF EXISTS customer_reps_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE customer_reps
          ADD CONSTRAINT customer_reps_rep_id_fkey
          FOREIGN KEY (rep_id) REFERENCES reps (id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )

    op.execute("ALTER TABLE distribution_log_entries DROP CONSTRAINT IF EXISTS distribution_log_entries_rep_id_fkey")
    op.execute(
        """
        DO $$
        BEGIN
          ALTER TABLE distribution_log_entries
          ADD CONSTRAINT distribution_log_entries_rep_id_fkey
          FOREIGN KEY (rep_id) REFERENCES reps (id) ON DELETE SET NULL;
        EXCEPTION WHEN duplicate_object THEN
          NULL;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE distribution_log_entries DROP CONSTRAINT IF EXISTS distribution_log_entries_rep_id_fkey")
    op.execute("ALTER TABLE customer_reps DROP CONSTRAINT IF EXISTS customer_reps_rep_id_fkey")
    op.execute("ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_primary_rep_id_fkey")

    op.execute("ALTER TABLE distribution_log_entries ADD CONSTRAINT distribution_log_entries_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES users (id) ON DELETE SET NULL")
    op.execute("ALTER TABLE customer_reps ADD CONSTRAINT customer_reps_rep_id_fkey FOREIGN KEY (rep_id) REFERENCES users (id) ON DELETE CASCADE")
    op.execute("ALTER TABLE customers ADD CONSTRAINT customers_primary_rep_id_fkey FOREIGN KEY (primary_rep_id) REFERENCES users (id) ON DELETE SET NULL")

    op.drop_index("idx_reps_name", table_name="reps")
    op.drop_table("reps")
