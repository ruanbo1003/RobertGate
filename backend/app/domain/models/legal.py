"""法律咨询领域模型。

- `LegalChatMessage`：持久化的对话消息（一个用户一个对话，消息按用户隔离）。
- `LawArticle`：民法典条文值对象，来自知识库（PDF 解析），不落库。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class LegalChatMessage(Base):
    __tablename__ = "legal_messages"
    __table_args__ = (Index("ix_legal_messages_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    # [{"article_no": 710, "label": "第七百一十条"}]；user 消息恒为空列表
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True)
class LawArticle:
    article_no: int
    label: str
    content: str
