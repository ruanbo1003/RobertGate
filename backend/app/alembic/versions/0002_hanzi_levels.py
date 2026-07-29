"""hanzi level refactor: drop hanzi_entries, add users.role, create levels/characters/user_progress

Revision ID: 0002_hanzi_levels
Revises: 0001_initial
Create Date: 2026-07-28
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_hanzi_levels"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) users.role
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=16),
            nullable=False,
            server_default="user",
        ),
    )

    # 2) drop legacy hanzi_entries (project pre-production; no data migration)
    op.drop_index("ix_hanzi_entries_char", table_name="hanzi_entries")
    op.drop_index("ix_hanzi_entries_user_id", table_name="hanzi_entries")
    op.drop_table("hanzi_entries")

    # 3) hanzi_levels
    op.create_table(
        "hanzi_levels",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hanzi_levels_name", "hanzi_levels", ["name"], unique=True)
    op.create_index("ix_hanzi_levels_order_index", "hanzi_levels", ["order_index"])

    # 4) hanzi_characters
    op.create_table(
        "hanzi_characters",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("level_id", sa.String(length=36), nullable=False),
        sa.Column("char", sa.String(length=4), nullable=False),
        sa.Column("pinyin", sa.String(length=32), nullable=False),
        sa.Column("meaning", sa.Text(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["level_id"], ["hanzi_levels.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_hanzi_characters_char", "hanzi_characters", ["char"], unique=True
    )
    op.create_index(
        "ix_hanzi_characters_level_id", "hanzi_characters", ["level_id"]
    )
    op.create_index(
        "ix_hanzi_characters_level_order",
        "hanzi_characters",
        ["level_id", "order_index"],
    )

    # 5) hanzi_user_progress
    op.create_table(
        "hanzi_user_progress",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["hanzi_characters.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "character_id", name="uq_hanzi_progress_user_char"
        ),
    )
    op.create_index(
        "ix_hanzi_progress_user_id", "hanzi_user_progress", ["user_id"]
    )
    op.create_index(
        "ix_hanzi_progress_character_id",
        "hanzi_user_progress",
        ["character_id"],
    )
    op.create_index(
        "ix_hanzi_progress_user_char",
        "hanzi_user_progress",
        ["user_id", "character_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hanzi_progress_user_char", table_name="hanzi_user_progress")
    op.drop_index(
        "ix_hanzi_progress_character_id", table_name="hanzi_user_progress"
    )
    op.drop_index("ix_hanzi_progress_user_id", table_name="hanzi_user_progress")
    op.drop_table("hanzi_user_progress")

    op.drop_index("ix_hanzi_characters_level_order", table_name="hanzi_characters")
    op.drop_index("ix_hanzi_characters_level_id", table_name="hanzi_characters")
    op.drop_index("ix_hanzi_characters_char", table_name="hanzi_characters")
    op.drop_table("hanzi_characters")

    op.drop_index("ix_hanzi_levels_order_index", table_name="hanzi_levels")
    op.drop_index("ix_hanzi_levels_name", table_name="hanzi_levels")
    op.drop_table("hanzi_levels")

    # Recreate hanzi_entries (matches 0001 shape)
    op.create_table(
        "hanzi_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("char", sa.String(length=4), nullable=False),
        sa.Column("learned", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("learned_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "char", name="uq_hanzi_user_char"),
    )
    op.create_index("ix_hanzi_entries_user_id", "hanzi_entries", ["user_id"])
    op.create_index("ix_hanzi_entries_char", "hanzi_entries", ["char"])

    op.drop_column("users", "role")
