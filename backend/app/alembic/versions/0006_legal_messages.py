"""legal messages: 法律咨询单会话消息（按用户隔离，citations 存 JSONB）

Revision ID: 0006_legal_messages
Revises: 0005_t2i_templates
Create Date: 2026-10-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006_legal_messages"
down_revision = "0005_t2i_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_messages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_legal_messages_user_id", "legal_messages", ["user_id"])
    op.create_index(
        "ix_legal_messages_user_created", "legal_messages", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_legal_messages_user_created", table_name="legal_messages")
    op.drop_index("ix_legal_messages_user_id", table_name="legal_messages")
    op.drop_table("legal_messages")
