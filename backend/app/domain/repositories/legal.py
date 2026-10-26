"""法律咨询消息仓储接口。"""

from __future__ import annotations

from typing import Protocol

from app.domain.models.legal import LegalChatMessage


class LegalMessageRepository(Protocol):
    async def list_by_user(self, user_id: str) -> list[LegalChatMessage]:
        """该用户全部消息，按 created_at 升序。"""
        ...

    async def last_n_by_user(self, user_id: str, n: int) -> list[LegalChatMessage]:
        """该用户最近 n 条消息，按 created_at 升序返回。"""
        ...

    def add(self, message: LegalChatMessage) -> None: ...

    async def delete_by_user(self, user_id: str) -> None: ...
