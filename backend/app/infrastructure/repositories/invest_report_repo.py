from __future__ import annotations

from sqlalchemy import func, select

from app.domain.models.invest_report import (
    IrChapter,
    IrChatMessage,
    IrProject,
    IrSample,
    IrSource,
    IrTemplate,
)
from app.infrastructure.repositories.base import SqlRepo


class IrSampleRepo(SqlRepo[IrSample]):
    model = IrSample

    async def list_by_type(self, type_: str) -> list[IrSample]:
        return await self._all(
            select(IrSample).where(IrSample.type == type_).order_by(IrSample.uploaded_at.asc())
        )


class IrTemplateRepo(SqlRepo[IrTemplate]):
    model = IrTemplate

    async def find_by_type(self, type_: str) -> IrTemplate | None:
        return await self._one(select(IrTemplate).where(IrTemplate.type == type_))


class IrProjectRepo(SqlRepo[IrProject]):
    model = IrProject

    async def list_page(self, page: int, page_size: int) -> tuple[list[IrProject], int]:
        total = await self._count(select(func.count(IrProject.id)))
        rows = await self._all(
            select(IrProject)
            .order_by(IrProject.updated_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        return rows, total


class IrChapterRepo(SqlRepo[IrChapter]):
    model = IrChapter

    async def list_by_project(self, project_id: int) -> list[IrChapter]:
        return await self._all(
            select(IrChapter)
            .where(IrChapter.project_id == project_id)
            .order_by(IrChapter.order_index.asc())
        )


class IrSourceRepo(SqlRepo[IrSource]):
    model = IrSource

    async def list_by_project(self, project_id: int) -> list[IrSource]:
        return await self._all(
            select(IrSource)
            .where(IrSource.project_id == project_id)
            .order_by(IrSource.uploaded_at.asc())
        )


class IrChatRepo(SqlRepo[IrChatMessage]):
    model = IrChatMessage

    async def list_by_project(self, project_id: int, limit: int = 50) -> list[IrChatMessage]:
        rows = await self._all(
            select(IrChatMessage)
            .where(IrChatMessage.project_id == project_id)
            .order_by(IrChatMessage.created_at.desc(), IrChatMessage.id.desc())
            .limit(limit)
        )
        return list(reversed(rows))
