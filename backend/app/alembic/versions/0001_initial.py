"""initial schema: users, hanzi_entries

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

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


def downgrade() -> None:
    op.drop_index("ix_hanzi_entries_char", table_name="hanzi_entries")
    op.drop_index("ix_hanzi_entries_user_id", table_name="hanzi_entries")
    op.drop_table("hanzi_entries")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
