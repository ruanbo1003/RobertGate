from sqlalchemy import func, select

from app.domain.models.hanzi import HanziCharacter
from app.infrastructure.repositories.base import SqlRepo


class HanziCharacterRepo(SqlRepo[HanziCharacter]):
    model = HanziCharacter

    async def list_by_level(self, level_id: str) -> list[HanziCharacter]:
        return await self._all(
            select(HanziCharacter)
            .where(HanziCharacter.level_id == level_id)
            .order_by(HanziCharacter.order_index.asc())
        )

    async def find_by_char(self, char: str) -> HanziCharacter | None:
        return await self._one(
            select(HanziCharacter).where(HanziCharacter.char == char)
        )

    async def existing_chars(self, chars: list[str]) -> set[str]:
        if not chars:
            return set()
        result = await self.session.execute(
            select(HanziCharacter.char).where(HanziCharacter.char.in_(chars))
        )
        return {c for c in result.scalars().all()}

    async def count_by_level(self, level_id: str) -> int:
        return await self._count(
            select(func.count(HanziCharacter.id)).where(
                HanziCharacter.level_id == level_id
            )
        )

    async def count_by_levels(self, level_ids: list[str]) -> dict[str, int]:
        if not level_ids:
            return {}
        result = await self.session.execute(
            select(HanziCharacter.level_id, func.count(HanziCharacter.id))
            .where(HanziCharacter.level_id.in_(level_ids))
            .group_by(HanziCharacter.level_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def max_order_index(self, level_id: str) -> int:
        result = await self.session.execute(
            select(func.max(HanziCharacter.order_index)).where(
                HanziCharacter.level_id == level_id
            )
        )
        value = result.scalar_one()
        return int(value) if value is not None else -1

    def add_many(self, characters: list[HanziCharacter]) -> None:
        if not characters:
            return
        self.session.add_all(characters)
