"""t2i tasks: tasks / images / image_blobs

Revision ID: 0004_t2i_tasks
Revises: 0003_hanzi_example_words
Create Date: 2026-08-10
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_t2i_tasks"
down_revision = "0003_hanzi_example_words"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "t2i_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("template_code", sa.String(length=32), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="generating"),
        sa.Column("last_failed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("keywords_hash", name="uq_t2i_tasks_keywords_hash"),
    )
    op.create_index("ix_t2i_tasks_template_code", "t2i_tasks", ["template_code"])
    op.create_index("ix_t2i_tasks_updated_at", "t2i_tasks", ["updated_at"])

    op.create_table(
        "t2i_images",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="generating"),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("mime", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["t2i_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_t2i_images_task_id", "t2i_images", ["task_id"])
    op.create_index("ix_t2i_images_created_at", "t2i_images", ["created_at"])

    op.create_table(
        "t2i_image_blobs",
        sa.Column("image_id", sa.String(length=36), nullable=False),
        sa.Column("bytes", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(["image_id"], ["t2i_images.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("image_id"),
    )


def downgrade() -> None:
    op.drop_table("t2i_image_blobs")
    op.drop_index("ix_t2i_images_created_at", table_name="t2i_images")
    op.drop_index("ix_t2i_images_task_id", table_name="t2i_images")
    op.drop_table("t2i_images")
    op.drop_index("ix_t2i_tasks_updated_at", table_name="t2i_tasks")
    op.drop_index("ix_t2i_tasks_template_code", table_name="t2i_tasks")
    op.drop_table("t2i_tasks")
