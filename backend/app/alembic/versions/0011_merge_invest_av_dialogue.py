"""合并双 head：0009_invest_reports 与 0010_av_dialogue

两条 feature 分支各自基于 0008 新增迁移，main 合并代码后 alembic 出现两个 head，
`upgrade head` 报 CommandError 导致应用启动失败。本迁移只做链路合流，不改表结构。

Revision ID: 0011_merge_invest_av_dialogue
Revises: 0009_invest_reports, 0010_av_dialogue
Create Date: 2026-11-12
"""

from __future__ import annotations

revision = "0011_merge_invest_av_dialogue"
down_revision = ("0009_invest_reports", "0010_av_dialogue")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
