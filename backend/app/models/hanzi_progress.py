from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
