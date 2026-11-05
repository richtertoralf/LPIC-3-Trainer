"""lab didactics: task, tools, success criteria, pitfalls, instructor notes, lab status, group labs

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("labs") as batch:
        batch.add_column(sa.Column("task_de", sa.Text(), nullable=False, server_default=""))
        for name in ("tools_de", "success_criteria_de", "pitfalls_de", "instructor_notes_de"):
            batch.add_column(sa.Column(name, sa.JSON(), nullable=False, server_default="[]"))
    with op.batch_alter_table("lab_progress") as batch:
        batch.add_column(
            sa.Column("status", sa.String(length=16), nullable=False, server_default="completed")
        )
        batch.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch.alter_column("completed_at", existing_type=sa.DateTime(), nullable=True)
    # existing rows were "completed" marks; they started when they were completed
    op.execute("UPDATE lab_progress SET started_at = completed_at WHERE started_at IS NULL")
    op.create_table(
        "group_labs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id", sa.Integer(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "lab_id", sa.Integer(), sa.ForeignKey("labs.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("group_id", "lab_id", name="uq_group_lab"),
    )


def downgrade() -> None:
    op.drop_table("group_labs")
    op.execute("DELETE FROM lab_progress WHERE status != 'completed'")
    with op.batch_alter_table("lab_progress") as batch:
        batch.alter_column("completed_at", existing_type=sa.DateTime(), nullable=False)
        batch.drop_column("started_at")
        batch.drop_column("status")
    with op.batch_alter_table("labs") as batch:
        for name in ("instructor_notes_de", "pitfalls_de", "success_criteria_de", "tools_de"):
            batch.drop_column(name)
        batch.drop_column("task_de")
