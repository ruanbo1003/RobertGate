"""t2i templates: dynamic template registry with single {{item}} placeholder

Revision ID: 0005_t2i_templates
Revises: 0004_t2i_tasks
Create Date: 2026-08-11
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0005_t2i_templates"
down_revision = "0004_t2i_tasks"
branch_labels = None
depends_on = None


ENGLISH_PRIMER_PROMPT = (
    "A cute flat cartoon illustration of a {{item}}, simple design, "
    "kids education style, plain white background, no text."
)
GENERAL_PROMPT = "{{item}}."


def upgrade() -> None:
    op.create_table(
        "t2i_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_t2i_templates_code"),
    )
    op.create_index(
        "ix_t2i_templates_order_index", "t2i_templates", ["order_index"]
    )

    # Seed: 把原来硬编码的两个模板迁进 DB（保持 code 不变，避免老 task 的 template_code 失效）
    now = datetime.now(timezone.utc)
    templates_table = sa.table(
        "t2i_templates",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("prompt", sa.Text),
        sa.column("order_index", sa.Integer),
        sa.column("is_builtin", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(
        templates_table,
        [
            {
                "id": str(uuid.uuid4()),
                "code": "english-primer",
                "name": "英文启蒙",
                "description": "给英文单词生成卡通配图，吸引小朋友",
                "prompt": ENGLISH_PRIMER_PROMPT,
                "order_index": 0,
                "is_builtin": False,
                "created_at": now,
                "updated_at": now,
            },
            {
                "id": str(uuid.uuid4()),
                "code": "general",
                "name": "常规",
                "description": "自由文生图，用于素材保存",
                "prompt": GENERAL_PROMPT,
                "order_index": 1,
                "is_builtin": False,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_t2i_templates_order_index", table_name="t2i_templates")
    op.drop_table("t2i_templates")
