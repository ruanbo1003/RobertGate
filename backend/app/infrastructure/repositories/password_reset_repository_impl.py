from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.password_reset import PasswordReset
from app.domain.repositories.password_reset_repository import PasswordResetRepository
from app.infrastructure.database.models import PasswordResetModel


class PasswordResetRepositoryImpl(PasswordResetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_domain(self, model: PasswordResetModel) -> PasswordReset:
        return PasswordReset(
            id=model.id,
            user_id=model.user_id,
            token=model.token,
            created_at=model.created_at,
            used=model.used,
        )

    def _to_model(self, reset: PasswordReset) -> PasswordResetModel:
        return PasswordResetModel(
            id=reset.id,
            user_id=reset.user_id,
            token=reset.token,
            created_at=reset.created_at,
            used=reset.used,
        )

    async def find_by_token(self, token: str) -> PasswordReset | None:
        result = await self._session.execute(
            select(PasswordResetModel).where(PasswordResetModel.token == token)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def save(self, reset: PasswordReset) -> None:
        self._session.add(self._to_model(reset))
        await self._session.commit()

    async def update(self, reset: PasswordReset) -> None:
        result = await self._session.execute(
            select(PasswordResetModel).where(PasswordResetModel.id == reset.id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.used = reset.used
            await self._session.commit()
