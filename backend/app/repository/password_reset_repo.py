from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordReset


class PasswordResetRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_token(self, token: str) -> PasswordReset | None:
        result = await self.session.execute(
            select(PasswordReset).where(PasswordReset.token == token)
        )
        return result.scalar_one_or_none()

    async def save(self, reset: PasswordReset) -> None:
        self.session.add(reset)
        await self.session.commit()

    async def update(self, reset: PasswordReset) -> None:
        await self.session.commit()
