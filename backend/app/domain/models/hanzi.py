from datetime import datetime

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


class HanziLevel(Base):
    __tablename__ = "hanzi_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, index=True, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


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
