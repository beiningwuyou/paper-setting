"""Constrain job mode to supported pipeline values.

Revision ID: 0004
Revises: 0003
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.create_check_constraint(
            "ck_jobs_mode",
            "mode IN ('format', 'template')",
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_constraint("ck_jobs_mode", type_="check")
