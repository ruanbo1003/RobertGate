from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def find_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def update(self, user: User) -> None: ...
