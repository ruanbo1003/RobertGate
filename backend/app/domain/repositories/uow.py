"""工作单元（Unit of Work）接口。

事务边界属于用例（application），不属于仓储：仓储只负责把实体挂进/摘出
持久化上下文，何时提交由 service 在用例结尾决定。
"""

from __future__ import annotations

from typing import Protocol

from app.domain.repositories.hanzi import (
    HanziCharacterRepository,
    HanziLevelRepository,
    HanziProgressRepository,
)
from app.domain.repositories.t2i import (
    T2IImageBlobRepository,
    T2IImageRepository,
    T2ITaskRepository,
    T2ITemplateRepository,
)
from app.domain.repositories.user import UserRepository


class UnitOfWork(Protocol):
    users: UserRepository
    hanzi_levels: HanziLevelRepository
    hanzi_characters: HanziCharacterRepository
    hanzi_progress: HanziProgressRepository
    t2i_templates: T2ITemplateRepository
    t2i_tasks: T2ITaskRepository
    t2i_images: T2IImageRepository
    t2i_blobs: T2IImageBlobRepository

    async def flush(self) -> None:
        """把挂起的写操作发到 DB 但不结束事务。

        只在同一用例内后续逻辑依赖 DB 侧定序/生成值时才需要（例如同一事务里
        先插父行再插子行的外键定序）。"""
        ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
