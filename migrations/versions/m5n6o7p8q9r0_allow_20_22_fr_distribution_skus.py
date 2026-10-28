"""Allow 20 Fr and 22 Fr catalogs on distribution rows.

Revision ID: m5n6o7p8q9r0
Revises: l4f5a6b7c8d9
Create Date: 2026-10-27 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "m5n6o7p8q9r0"
down_revision: Union[str, Sequence[str], None] = "l4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW = "sku IN ('211410SPT','211610SPT','211810SPT','212010SPT','212210SPT')"
_OLD = "sku IN ('211810SPT','211610SPT','211410SPT')"


def upgrade() -> None:
    op.drop_constraint("ck_distribution_log_sku", "distribution_log_entries", type_="check")
    op.create_check_constraint("ck_distribution_log_sku", "distribution_log_entries", _NEW)
    op.drop_constraint("ck_distribution_lines_sku", "distribution_lines", type_="check")
    op.create_check_constraint("ck_distribution_lines_sku", "distribution_lines", _NEW)


def downgrade() -> None:
    op.drop_constraint("ck_distribution_lines_sku", "distribution_lines", type_="check")
    op.create_check_constraint("ck_distribution_lines_sku", "distribution_lines", _OLD)
    op.drop_constraint("ck_distribution_log_sku", "distribution_log_entries", type_="check")
    op.create_check_constraint("ck_distribution_log_sku", "distribution_log_entries", _OLD)
