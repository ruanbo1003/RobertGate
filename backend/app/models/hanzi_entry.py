from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HanziEntry(Base):
    __tablename__ = "hanzi_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "char", name="uq_hanzi_user_char"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    char: Mapped[str] = mapped_column(String(4), index=True)
    learned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    learned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
