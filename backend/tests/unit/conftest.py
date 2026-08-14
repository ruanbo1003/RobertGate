"""单元测试共享夹具：假 UnitOfWork。

service 现在只依赖 UnitOfWork，测试用一个带 8 个 mock 仓储 + commit/rollback
的简单对象顶替。`add` / `add_many` 是同步方法，必须用 MagicMock —— 用
AsyncMock 会返回一个没人 await 的 coroutine。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

REPO_NAMES = (
    "users",
    "hanzi_levels",
    "hanzi_characters",
    "hanzi_progress",
    "t2i_templates",
    "t2i_tasks",
    "t2i_images",
    "t2i_blobs",
)


def make_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.add = MagicMock()
    repo.add_many = MagicMock()
    return repo


class FakeUow:
    def __init__(self) -> None:
        for name in REPO_NAMES:
            setattr(self, name, make_repo())
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()


def make_uow() -> FakeUow:
    return FakeUow()


@pytest.fixture
def uow() -> FakeUow:
    return make_uow()
