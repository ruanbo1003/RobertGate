"""单元测试共享夹具：假 UnitOfWork。

service 现在只依赖 UnitOfWork，测试用一个带 8 个 mock 仓储 + flush/commit/rollback
的简单对象顶替。`add` / `add_many` 是同步方法，必须用 MagicMock —— 用
AsyncMock 会返回一个没人 await 的 coroutine。

FakeUow 还按调用顺序记一份事件日志 `uow.calls`（形如
`["t2i_tasks.add", "flush", "t2i_images.add", "commit"]`），用来断言**顺序不变量**
——只数 await_count 的话，把 commit 挪到 spawn 之后测试照样绿。
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


def make_repo(name: str = "repo", log: list[str] | None = None) -> AsyncMock:
    log = log if log is not None else []
    repo = AsyncMock()
    repo.add = MagicMock(side_effect=lambda _entity: log.append(f"{name}.add"))
    repo.add_many = MagicMock(side_effect=lambda _entities: log.append(f"{name}.add_many"))
    repo.delete = AsyncMock(side_effect=lambda _entity: log.append(f"{name}.delete"))
    return repo


class FakeUow:
    def __init__(self) -> None:
        self.calls: list[str] = []
        for name in REPO_NAMES:
            setattr(self, name, make_repo(name, self.calls))
        self.flush = AsyncMock(side_effect=lambda: self.calls.append("flush"))
        self.commit = AsyncMock(side_effect=lambda: self.calls.append("commit"))
        self.rollback = AsyncMock(side_effect=lambda: self.calls.append("rollback"))


def make_uow() -> FakeUow:
    return FakeUow()


@pytest.fixture
def uow() -> FakeUow:
    return make_uow()
