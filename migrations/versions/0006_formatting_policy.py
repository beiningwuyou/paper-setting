"""Persist formatting mode; existing tasks retain their original behavior."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.add_column(
            sa.Column(
                "formatting_mode",
                sa.String(16),
                nullable=False,
                server_default="preserve",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("jobs") as batch:
        batch.drop_column("formatting_mode")
