from __future__ import annotations

from sqlalchemy import delete, func, select

from app.domain.models.ai_video import (
    AvCharacter,
    AvCharacterImage,
    AvProject,
    AvProjectCharacter,
    AvShot,
)
from app.infrastructure.repositories.base import SqlRepo


class AvCharacterRepo(SqlRepo[AvCharacter]):
    model = AvCharacter

    async def find_by_name(self, name: str) -> AvCharacter | None:
        return await self._one(select(AvCharacter).where(AvCharacter.name == name))

    async def list_all(self) -> list[AvCharacter]:
        return await self._all(select(AvCharacter).order_by(AvCharacter.updated_at.desc()))


class AvCharacterImageRepo(SqlRepo[AvCharacterImage]):
    model = AvCharacterImage

    async def list_by_character(self, character_id: int) -> list[AvCharacterImage]:
        return await self._all(
            select(AvCharacterImage)
            .where(AvCharacterImage.character_id == character_id)
            .order_by(AvCharacterImage.created_at.asc(), AvCharacterImage.id.asc())
        )


class AvProjectRepo(SqlRepo[AvProject]):
    model = AvProject

    async def list_page(self, page: int, page_size: int) -> tuple[list[AvProject], int]:
        total = await self._count(select(func.count(AvProject.id)))
        rows = await self._all(
            select(AvProject)
            .order_by(AvProject.updated_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return rows, total


class AvProjectCharacterRepo(SqlRepo[AvProjectCharacter]):
    model = AvProjectCharacter

    async def list_by_project(self, project_id: int) -> list[AvProjectCharacter]:
        return await self._all(
            select(AvProjectCharacter).where(AvProjectCharacter.project_id == project_id)
        )

    async def list_by_character(self, character_id: int) -> list[AvProjectCharacter]:
        return await self._all(
            select(AvProjectCharacter).where(AvProjectCharacter.character_id == character_id)
        )

    async def used_counts(self) -> dict[int, int]:
        result = await self.session.execute(
            select(
                AvProjectCharacter.character_id,
                func.count(AvProjectCharacter.project_id),
            ).group_by(AvProjectCharacter.character_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}


class AvShotRepo(SqlRepo[AvShot]):
    model = AvShot

    async def list_by_project(self, project_id: int) -> list[AvShot]:
        return await self._all(
            select(AvShot)
            .where(AvShot.project_id == project_id)
            .order_by(AvShot.order_index.asc())
        )

    async def delete_by_project(self, project_id: int) -> None:
        await self.session.execute(delete(AvShot).where(AvShot.project_id == project_id))
