"""用户仓储接口。

结构化协议（Protocol）：infrastructure 里的实现类不继承本接口，
靠方法签名匹配。application 只依赖这里的抽象。
"""

from __future__ import annotations

from typing import Protocol

from app.domain.models.user import User


class UserRepository(Protocol):
    async def find_by_id(self, id_: str) -> User | None: ...

    async def find_by_email(self, email: str) -> User | None: ...

    async def find_by_username(self, username: str) -> User | None: ...

    def add(self, entity: User) -> None: ...
