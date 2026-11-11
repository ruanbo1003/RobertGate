"""av_shots: 新增 dialogue 台词列表列（旧单台词回填）；av_characters: 新增 voice_desc

Revision ID: 0010_av_dialogue
Revises: 0008_av_multiref_video_prompt
Create Date: 2026-11-09
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0010_av_dialogue"
down_revision = "0008_av_multiref_video_prompt"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "av_shots",
        sa.Column("dialogue", JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "av_characters",
        sa.Column("voice_desc", sa.String(200), nullable=False, server_default=""),
    )
    op.execute(
        """
        UPDATE av_shots
        SET dialogue = jsonb_build_array(
            jsonb_build_object(
                'character_id', speaker_character_id,
                'en', trim(line_en),
                'zh', trim(coalesce(line_zh, ''))
            )
        )
        WHERE trim(line_en) != ''
        """
    )


def downgrade() -> None:
    op.drop_column("av_characters", "voice_desc")
    op.drop_column("av_shots", "dialogue")
