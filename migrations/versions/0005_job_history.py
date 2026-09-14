"""Add the stable job-history pagination index.

Revision ID: 0005
Revises: 0004
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(sa.Column("template_filename", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("template_sha256", sa.String(length=64), nullable=True))
    op.create_index("idx_jobs_created_id", "jobs", ["created_at", "id"])


def downgrade() -> None:
    op.drop_index("idx_jobs_created_id", table_name="jobs")
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("template_sha256")
        batch.drop_column("template_filename")
