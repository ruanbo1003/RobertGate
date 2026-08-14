from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.hanzi import HanziCharacter, HanziUserProgress


class HanziProgressRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find(self, user_id: str, character_id: str) -> HanziUserProgress | None:
        result = await self.session.execute(
            select(HanziUserProgress).where(
                HanziUserProgress.user_id == user_id,
                HanziUserProgress.character_id == character_id,
            )
        )
        return result.scalar_one_or_none()

    async def learned_ids_by_level(
        self, user_id: str, level_id: str
    ) -> set[str]:
        """当前用户在指定 level 下已学的 character_id 集合。"""
        result = await self.session.execute(
            select(HanziUserProgress.character_id)
            .join(
                HanziCharacter,
                HanziCharacter.id == HanziUserProgress.character_id,
            )
            .where(
                HanziUserProgress.user_id == user_id,
                HanziCharacter.level_id == level_id,
            )
        )
        return {cid for cid in result.scalars().all()}

    async def progress_map_by_level(
        self, user_id: str, level_id: str
    ) -> dict[str, HanziUserProgress]:
        result = await self.session.execute(
            select(HanziUserProgress)
            .join(
                HanziCharacter,
                HanziCharacter.id == HanziUserProgress.character_id,
            )
            .where(
                HanziUserProgress.user_id == user_id,
                HanziCharacter.level_id == level_id,
            )
        )
        return {p.character_id: p for p in result.scalars().all()}

    async def learned_count_by_levels(
        self, user_id: str, level_ids: list[str]
    ) -> dict[str, int]:
        if not level_ids:
            return {}
        result = await self.session.execute(
            select(HanziCharacter.level_id, func.count(HanziUserProgress.id))
            .join(
                HanziCharacter,
                HanziCharacter.id == HanziUserProgress.character_id,
            )
            .where(
                HanziUserProgress.user_id == user_id,
                HanziCharacter.level_id.in_(level_ids),
            )
            .group_by(HanziCharacter.level_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def save(self, progress: HanziUserProgress) -> None:
        self.session.add(progress)
        await self.session.commit()

    async def delete(self, progress: HanziUserProgress) -> None:
        await self.session.delete(progress)
        await self.session.commit()
