"""source url and exam code of import batches

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_batches") as batch:
        batch.add_column(
            sa.Column("source_url", sa.String(length=255), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("exam_code", sa.String(length=16), nullable=False, server_default="")
        )
    # LPIC-3 exam codes are <module>-300 for the version 3.0 objectives.
    op.execute(
        "UPDATE import_batches SET exam_code = module_code || '-300' "
        "WHERE kind = 'questions' AND exam_code = '' AND module_code != ''"
    )


def downgrade() -> None:
    with op.batch_alter_table("import_batches") as batch:
        batch.drop_column("exam_code")
        batch.drop_column("source_url")
