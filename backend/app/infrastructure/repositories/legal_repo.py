from sqlalchemy import delete, select

from app.domain.models.legal import LegalChatMessage
from app.infrastructure.repositories.base import SqlRepo


class LegalMessageRepo(SqlRepo[LegalChatMessage]):
    model = LegalChatMessage

    async def list_by_user(self, user_id: str) -> list[LegalChatMessage]:
        return await self._all(
            select(LegalChatMessage)
            .where(LegalChatMessage.user_id == user_id)
            .order_by(LegalChatMessage.created_at.asc())
        )

    async def last_n_by_user(self, user_id: str, n: int) -> list[LegalChatMessage]:
        recent = await self._all(
            select(LegalChatMessage)
            .where(LegalChatMessage.user_id == user_id)
            .order_by(LegalChatMessage.created_at.desc())
            .limit(n)
        )
        return list(reversed(recent))

    async def delete_by_user(self, user_id: str) -> None:
        await self.session.execute(
            delete(LegalChatMessage).where(LegalChatMessage.user_id == user_id)
        )
