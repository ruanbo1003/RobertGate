from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.hanzi import HanziLevel


class HanziLevelRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self) -> list[HanziLevel]:
        result = await self.session.execute(
            select(HanziLevel).order_by(HanziLevel.order_index.asc())
        )
        return list(result.scalars().all())

    async def find_by_id(self, level_id: str) -> HanziLevel | None:
        result = await self.session.execute(
            select(HanziLevel).where(HanziLevel.id == level_id)
        )
        return result.scalar_one_or_none()

    async def find_by_name(self, name: str) -> HanziLevel | None:
        result = await self.session.execute(
            select(HanziLevel).where(HanziLevel.name == name)
        )
        return result.scalar_one_or_none()

    async def save(self, level: HanziLevel) -> None:
        self.session.add(level)
        await self.session.commit()

    async def update(self, level: HanziLevel) -> None:
        await self.session.commit()

    async def delete(self, level: HanziLevel) -> None:
        await self.session.delete(level)
        await self.session.commit()
