from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base

HANZI_RE = re.compile(r"^[\u4e00-\u9fa5]$")
HANZI_EXTRACT_RE = re.compile(r"[\u4e00-\u9fa5]")

MAX_EXAMPLE_WORDS = 20
MAX_EXAMPLE_WORD_LEN = 16


def _now() -> datetime:
    return datetime.now(timezone.utc)


def extract_hanzi(text: str) -> list[str]:
    """从任意文本抽取汉字，按出现顺序去重。"""
    seen: set[str] = set()
    result: list[str] = []
    for ch in HANZI_EXTRACT_RE.findall(text):
        if ch not in seen:
            seen.add(ch)
            result.append(ch)
    return result


def clean_example_words(v: list[str] | None) -> list[str] | None:
    """规范化例词列表：去空白项、逐项长度上限、总条数上限。

    非法输入抛 ValueError —— 调用方是 Pydantic field_validator，靠它转 422。
    """
    if v is None:
        return None
    cleaned: list[str] = []
    for w in v:
        if not isinstance(w, str):
            raise ValueError("example_words 每项必须是字符串")
        w = w.strip()
        if not w:
            continue
        if len(w) > MAX_EXAMPLE_WORD_LEN:
            raise ValueError(f"example_words 单项超过 {MAX_EXAMPLE_WORD_LEN} 字符")
        cleaned.append(w)
    if len(cleaned) > MAX_EXAMPLE_WORDS:
        raise ValueError(f"example_words 上限 {MAX_EXAMPLE_WORDS} 条")
    return cleaned


class HanziLevel(Base):
    __tablename__ = "hanzi_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, index=True, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def new(
        cls, name: str, description: str | None, order_index: int
    ) -> HanziLevel:
        now = _now()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        self.updated_at = _now()


class HanziCharacter(Base):
    __tablename__ = "hanzi_characters"
    __table_args__ = (
        Index("ix_hanzi_characters_level_order", "level_id", "order_index"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    level_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hanzi_levels.id", ondelete="RESTRICT"),
        index=True,
    )
    char: Mapped[str] = mapped_column(String(4), unique=True, index=True)
    pinyin: Mapped[str] = mapped_column(String(32))
    example_words: Mapped[list[str]] = mapped_column(JSONB, default=list)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def new(
        cls,
        level_id: str,
        char: str,
        pinyin: str,
        example_words: list[str] | None,
        order_index: int,
    ) -> HanziCharacter:
        now = _now()
        return cls(
            id=str(uuid.uuid4()),
            level_id=level_id,
            char=char,
            pinyin=pinyin,
            example_words=example_words or [],
            order_index=order_index,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        self.updated_at = _now()


class HanziUserProgress(Base):
    __tablename__ = "hanzi_user_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "character_id", name="uq_hanzi_progress_user_char"),
        Index("ix_hanzi_progress_user_char", "user_id", "character_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    character_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hanzi_characters.id", ondelete="CASCADE"),
        index=True,
    )
    learned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    @classmethod
    def new(cls, user_id: str, character_id: str) -> HanziUserProgress:
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            character_id=character_id,
            learned_at=_now(),
        )
