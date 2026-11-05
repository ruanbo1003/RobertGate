"""av_shots: 单参考角色升级为出场角色列表 + 新增图生视频提示

Revision ID: 0008_av_multiref_video_prompt
Revises: 0007_ai_videos
Create Date: 2026-11-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_av_multiref_video_prompt"
down_revision = "0007_ai_videos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "av_shots",
        sa.Column("video_prompt", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "av_shots",
        sa.Column("ref_character_ids", JSONB(), nullable=False, server_default="[]"),
    )
    op.execute(
        "UPDATE av_shots SET ref_character_ids = jsonb_build_array(ref_character_id) "
        "WHERE ref_character_id IS NOT NULL"
    )
    op.drop_column("av_shots", "ref_character_id")


def downgrade() -> None:
    op.add_column(
        "av_shots", sa.Column("ref_character_id", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE av_shots SET ref_character_id = (ref_character_ids->>0)::int "
        "WHERE jsonb_array_length(ref_character_ids) > 0"
    )
    op.drop_column("av_shots", "ref_character_ids")
    op.drop_column("av_shots", "video_prompt")
