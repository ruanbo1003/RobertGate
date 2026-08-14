"""SQLAlchemy 工作单元实现。

一个 UoW 绑定一个 session：8 个仓储按需惰性创建并缓存，彼此共享同一个
持久化上下文，因此一次 commit 覆盖本用例内的全部写操作。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.session import async_session
from app.infrastructure.repositories.hanzi_character_repo import HanziCharacterRepo
from app.infrastructure.repositories.hanzi_level_repo import HanziLevelRepo
from app.infrastructure.repositories.hanzi_progress_repo import HanziProgressRepo
from app.infrastructure.repositories.t2i_repo import (
    T2IImageBlobRepo,
    T2IImageRepo,
    T2ITaskRepo,
    T2ITemplateRepo,
)
from app.infrastructure.repositories.user_repo import UserRepo


class SqlUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @cached_property
    def users(self) -> UserRepo:
        return UserRepo(self.session)

    @cached_property
    def hanzi_levels(self) -> HanziLevelRepo:
        return HanziLevelRepo(self.session)

    @cached_property
    def hanzi_characters(self) -> HanziCharacterRepo:
        return HanziCharacterRepo(self.session)

    @cached_property
    def hanzi_progress(self) -> HanziProgressRepo:
        return HanziProgressRepo(self.session)

    @cached_property
    def t2i_templates(self) -> T2ITemplateRepo:
        return T2ITemplateRepo(self.session)

    @cached_property
    def t2i_tasks(self) -> T2ITaskRepo:
        return T2ITaskRepo(self.session)

    @cached_property
    def t2i_images(self) -> T2IImageRepo:
        return T2IImageRepo(self.session)

    @cached_property
    def t2i_blobs(self) -> T2IImageBlobRepo:
        return T2IImageBlobRepo(self.session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()


@asynccontextmanager
async def new_uow() -> AsyncIterator[SqlUnitOfWork]:
    """脱离请求生命周期时（后台任务）自开 session 的 UoW 工厂。"""
    async with async_session() as session:
        try:
            yield SqlUnitOfWork(session)
        except Exception:
            await session.rollback()
            raise
