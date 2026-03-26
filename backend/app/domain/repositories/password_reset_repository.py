from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.password_reset import PasswordReset


class PasswordResetRepository(ABC):
    @abstractmethod
    async def find_by_token(self, token: str) -> PasswordReset | None: ...

    @abstractmethod
    async def save(self, reset: PasswordReset) -> None: ...

    @abstractmethod
    async def update(self, reset: PasswordReset) -> None: ...
