from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
