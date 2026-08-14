from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.hanzi import HanziCharacter


class HanziCharacterRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_level(self, level_id: str) -> list[HanziCharacter]:
        result = await self.session.execute(
            select(HanziCharacter)
            .where(HanziCharacter.level_id == level_id)
            .order_by(HanziCharacter.order_index.asc())
        )
        return list(result.scalars().all())

    async def find_by_id(self, character_id: str) -> HanziCharacter | None:
        result = await self.session.execute(
            select(HanziCharacter).where(HanziCharacter.id == character_id)
        )
        return result.scalar_one_or_none()

    async def find_by_char(self, char: str) -> HanziCharacter | None:
        result = await self.session.execute(
            select(HanziCharacter).where(HanziCharacter.char == char)
        )
        return result.scalar_one_or_none()

    async def existing_chars(self, chars: list[str]) -> set[str]:
        if not chars:
            return set()
        result = await self.session.execute(
            select(HanziCharacter.char).where(HanziCharacter.char.in_(chars))
        )
        return {c for c in result.scalars().all()}

    async def count_by_level(self, level_id: str) -> int:
        result = await self.session.execute(
            select(func.count(HanziCharacter.id)).where(
                HanziCharacter.level_id == level_id
            )
        )
        return int(result.scalar_one() or 0)

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

    async def save(self, character: HanziCharacter) -> None:
        self.session.add(character)
        await self.session.commit()

    async def save_many(self, characters: list[HanziCharacter]) -> None:
        if not characters:
            return
        self.session.add_all(characters)
        await self.session.commit()

    async def update(self, character: HanziCharacter) -> None:
        await self.session.commit()

    async def delete(self, character: HanziCharacter) -> None:
        await self.session.delete(character)
        await self.session.commit()
