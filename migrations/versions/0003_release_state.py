"""release state and exam version of import batches

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_batches") as batch:
        batch.add_column(
            sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("exam_version", sa.String(length=16), nullable=False, server_default="")
        )
    # Bundled project questions form the released core pool; external imports stay unreleased.
    op.execute(
        "UPDATE import_batches SET released = 1, exam_version = '3.0' "
        "WHERE bundled = 1 AND supplementary = 0"
    )
    op.execute("UPDATE import_batches SET exam_version = '3.0' WHERE exam_version = ''")
    # Previously imported external questions were visible to their importer's groups at once.
    # From now on every non-bundled import is an unreleased supplementary pool.
    op.execute(
        "UPDATE import_batches SET supplementary = 1 WHERE bundled = 0 AND kind = 'questions'"
    )
    op.execute(
        "UPDATE questions SET supplementary = 1 WHERE import_batch_id IN "
        "(SELECT id FROM import_batches WHERE supplementary = 1)"
    )


def downgrade() -> None:
    with op.batch_alter_table("import_batches") as batch:
        batch.drop_column("exam_version")
        batch.drop_column("released")
