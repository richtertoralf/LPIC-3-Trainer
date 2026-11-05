"""fill-in-the-blank questions: case sensitivity flag

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.add_column(
            sa.Column("case_sensitive", sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_column("case_sensitive")
