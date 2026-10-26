from sqlalchemy import select

from app.domain.models.hanzi import HanziLevel
from app.infrastructure.repositories.base import SqlRepo


class HanziLevelRepo(SqlRepo[HanziLevel]):
    model = HanziLevel

    async def list_all(self) -> list[HanziLevel]:
        return await self._all(
            select(HanziLevel).order_by(HanziLevel.order_index.asc())
        )

    async def find_by_name(self, name: str) -> HanziLevel | None:
        return await self._one(select(HanziLevel).where(HanziLevel.name == name))
