"""documentation reference per question

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.add_column(
            sa.Column("reference", sa.String(length=255), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch:
        batch.drop_column("reference")
