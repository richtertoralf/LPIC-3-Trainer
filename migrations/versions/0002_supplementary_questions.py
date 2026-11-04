"""supplementary question pools enabled per group

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_batches") as batch:
        batch.add_column(
            sa.Column("supplementary", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("source", sa.String(length=160), nullable=False, server_default="")
        )
        batch.add_column(
            sa.Column("rights", sa.String(length=32), nullable=False, server_default="unknown")
        )
    with op.batch_alter_table("questions") as batch:
        batch.add_column(
            sa.Column("supplementary", sa.Boolean(), nullable=False, server_default=sa.false())
        )
    op.create_table(
        "group_sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("enabled_by", sa.Integer(), nullable=True),
        sa.Column("enabled_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enabled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "batch_id", name="uq_group_source"),
    )
    op.create_index("ix_questions_supplementary", "questions", ["supplementary"])


def downgrade() -> None:
    op.drop_index("ix_questions_supplementary", table_name="questions")
    op.drop_table("group_sources")
    with op.batch_alter_table("questions") as batch:
        batch.drop_column("supplementary")
    with op.batch_alter_table("import_batches") as batch:
        batch.drop_column("rights")
        batch.drop_column("source")
        batch.drop_column("supplementary")
