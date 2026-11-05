"""ai videos: 英语启蒙短视频工作台（角色 / 设定图 / 项目 / 项目角色关联 / 分镜）

Revision ID: 0007_ai_videos
Revises: 0006_legal_messages
Create Date: 2026-11-04
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_ai_videos"
down_revision = "0006_legal_messages"
branch_labels = None
depends_on = None


def _asset_columns(prefix: str) -> list[sa.Column]:
    return [
        sa.Column(f"{prefix}_state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column(f"{prefix}_path", sa.String(length=255), nullable=True),
        sa.Column(f"{prefix}_model", sa.String(length=128), nullable=False, server_default=""),
        sa.Column(f"{prefix}_stale", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(f"{prefix}_error", sa.Text(), nullable=True),
        sa.Column(f"{prefix}_version", sa.Integer(), nullable=False, server_default="0"),
    ]


def upgrade() -> None:
    op.create_table(
        "av_characters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("appearance_prompt", sa.Text(), nullable=False),
        sa.Column("personality", sa.Text(), nullable=True),
        sa.Column("cover_image_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_av_characters_name"),
    )
    op.create_index("ix_av_characters_updated_at", "av_characters", ["updated_at"])

    op.create_table(
        "av_character_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["av_characters.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_av_character_images_character_id", "av_character_images", ["character_id"]
    )

    op.create_table(
        "av_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("synopsis", sa.Text(), nullable=False),
        sa.Column("target_duration", sa.Integer(), nullable=False),
        sa.Column("default_models", JSONB(), nullable=False),
        sa.Column("tts_voice", sa.String(length=64), nullable=False),
        sa.Column("script", JSONB(), nullable=True),
        sa.Column("compose_state", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("compose_path", sa.String(length=255), nullable=True),
        sa.Column("compose_error", sa.Text(), nullable=True),
        sa.Column("compose_stale", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_av_projects_updated_at", "av_projects", ["updated_at"])

    op.create_table(
        "av_project_characters",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("character_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", "character_id"),
        sa.ForeignKeyConstraint(["project_id"], ["av_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["av_characters.id"], ondelete="RESTRICT"
        ),
    )

    op.create_table(
        "av_shots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("duration_estimate", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("speaker_character_id", sa.Integer(), nullable=True),
        sa.Column("ref_character_id", sa.Integer(), nullable=True),
        sa.Column("line_en", sa.Text(), nullable=False, server_default=""),
        sa.Column("line_zh", sa.Text(), nullable=False, server_default=""),
        sa.Column("image_prompt", sa.Text(), nullable=False, server_default=""),
        *_asset_columns("image"),
        *_asset_columns("video"),
        *_asset_columns("audio"),
        sa.Column("audio_voice", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("audio_duration", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["av_projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_av_shots_project_id", "av_shots", ["project_id"])
    op.create_index("ix_av_shots_order_index", "av_shots", ["order_index"])


def downgrade() -> None:
    op.drop_index("ix_av_shots_order_index", table_name="av_shots")
    op.drop_index("ix_av_shots_project_id", table_name="av_shots")
    op.drop_table("av_shots")
    op.drop_table("av_project_characters")
    op.drop_index("ix_av_projects_updated_at", table_name="av_projects")
    op.drop_table("av_projects")
    op.drop_index("ix_av_character_images_character_id", table_name="av_character_images")
    op.drop_table("av_character_images")
    op.drop_index("ix_av_characters_updated_at", table_name="av_characters")
    op.drop_table("av_characters")
