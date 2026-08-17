from sqlalchemy import func, select

from app.domain.models.hanzi import HanziCharacter, HanziUserProgress
from app.infrastructure.repositories.base import SqlRepo


class HanziProgressRepo(SqlRepo[HanziUserProgress]):
    model = HanziUserProgress

    async def find(self, user_id: str, character_id: str) -> HanziUserProgress | None:
        return await self._one(
            select(HanziUserProgress).where(
                HanziUserProgress.user_id == user_id,
                HanziUserProgress.character_id == character_id,
            )
        )

    async def progress_map_by_level(
        self, user_id: str, level_id: str
    ) -> dict[str, HanziUserProgress]:
        rows = await self._all(
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
        return {p.character_id: p for p in rows}

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
