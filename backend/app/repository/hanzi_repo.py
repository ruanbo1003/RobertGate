from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hanzi_entry import HanziEntry


class HanziRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_user(self, user_id: str) -> list[HanziEntry]:
        result = await self.session.execute(
            select(HanziEntry)
            .where(HanziEntry.user_id == user_id)
            .order_by(HanziEntry.created_at.asc())
        )
        return list(result.scalars().all())

    async def find(self, user_id: str, char: str) -> HanziEntry | None:
        result = await self.session.execute(
            select(HanziEntry).where(
                HanziEntry.user_id == user_id, HanziEntry.char == char
            )
        )
        return result.scalar_one_or_none()

    async def existing_chars(self, user_id: str, chars: list[str]) -> set[str]:
        if not chars:
            return set()
        result = await self.session.execute(
            select(HanziEntry.char).where(
                HanziEntry.user_id == user_id, HanziEntry.char.in_(chars)
            )
        )
        return {row for row in result.scalars().all()}

    async def add_many(self, entries: list[HanziEntry]) -> None:
        self.session.add_all(entries)
        await self.session.commit()

    async def update(self, entry: HanziEntry) -> None:
        await self.session.commit()

    async def delete(self, entry: HanziEntry) -> None:
        await self.session.delete(entry)
        await self.session.commit()
