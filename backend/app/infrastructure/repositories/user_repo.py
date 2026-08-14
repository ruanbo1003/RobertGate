from sqlalchemy import select

from app.domain.models.user import User
from app.infrastructure.repositories.base import SqlRepo


class UserRepo(SqlRepo[User]):
    model = User

    async def find_by_email(self, email: str) -> User | None:
        return await self._one(select(User).where(User.email == email))

    async def find_by_username(self, username: str) -> User | None:
        return await self._one(select(User).where(User.username == username))
