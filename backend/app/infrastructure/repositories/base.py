"""SQLAlchemy 仓储基类。

只负责持久化上下文的挂载/摘除与查询模板，**不提交事务**——commit 由
application 层的用例通过 UnitOfWork 决定（见 domain/repositories/uow.py）。
"""

from __future__ import annotations

from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


class SqlRepo(Generic[M]):
    model: ClassVar[type]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(self, id_: str) -> M | None:
        return await self.session.get(self.model, id_)

    def add(self, entity: M) -> None:
        self.session.add(entity)

    async def delete(self, entity: M) -> None:
        await self.session.delete(entity)

    # ---------- 查询模板 ----------

    async def _one(self, stmt: Any) -> M | None:
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _all(self, stmt: Any) -> list[M]:
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _count(self, stmt: Any) -> int:
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)
