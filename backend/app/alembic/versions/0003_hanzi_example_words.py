"""hanzi_characters: add example_words, drop meaning

Revision ID: 0003_hanzi_example_words
Revises: 0002_hanzi_levels
Create Date: 2026-08-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_hanzi_example_words"
down_revision = "0002_hanzi_levels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hanzi_characters",
        sa.Column(
            "example_words",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.drop_column("hanzi_characters", "meaning")


def downgrade() -> None:
    op.add_column(
        "hanzi_characters",
        sa.Column("meaning", sa.Text(), nullable=True),
    )
    op.drop_column("hanzi_characters", "example_words")
