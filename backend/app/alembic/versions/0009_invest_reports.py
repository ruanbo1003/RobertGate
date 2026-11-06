"""invest reports: 投资报告 Agent（范本/模板/项目/章节/资料/对话）

Revision ID: 0009_invest_reports
Revises: 0008_av_multiref_video_prompt
Create Date: 2026-11-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009_invest_reports"
down_revision = "0008_av_multiref_video_prompt"
branch_labels = None
depends_on = None

_EMPTY_CONTENT = '{"paragraphs": [], "citations": [], "tbds": []}'


def upgrade() -> None:
    op.create_table(
        "ir_samples",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(length=16), nullable=False, index=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=255), nullable=False),
        sa.Column("parse_state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("parsed_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ir_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type", sa.String(length=16), nullable=False, unique=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("chapters", JSONB(), nullable=False, server_default="[]"),
        sa.Column("style_notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("learned_from", JSONB(), nullable=False, server_default="[]"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ir_projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_table(
        "ir_chapters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id", sa.Integer(),
            sa.ForeignKey("ir_projects.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, index=True),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", JSONB(), nullable=False, server_default=_EMPTY_CONTENT),
    )
    op.create_table(
        "ir_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id", sa.Integer(),
            sa.ForeignKey("ir_projects.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("file_path", sa.String(length=255), nullable=True),
        sa.Column("parse_state", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("quality", sa.String(length=8), nullable=False, server_default="ok"),
        sa.Column("parsed_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ir_chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "project_id", sa.Integer(),
            sa.ForeignKey("ir_projects.id", ondelete="CASCADE"), nullable=False, index=True,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("updated_chapter_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    for table in (
        "ir_chat_messages", "ir_sources", "ir_chapters",
        "ir_projects", "ir_templates", "ir_samples",
    ):
        op.drop_table(table)
