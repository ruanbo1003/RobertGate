from __future__ import annotations

import uuid
from datetime import datetime, timezone


class User:
    """用户领域模型"""

    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        hashed_password: str,
        created_at: datetime,
        login_attempts: int = 0,
        locked_until: datetime | None = None,
    ) -> None:
        self.id = id
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
        self.created_at = created_at
        self.login_attempts = login_attempts
        self.locked_until = locked_until

    @staticmethod
    def create(username: str, email: str, hashed_password: str) -> User:
        return User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=hashed_password,
            created_at=datetime.now(timezone.utc),
        )

    @property
    def is_locked(self) -> bool:
        if self.locked_until is None:
            return False
        locked = self.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked

    def record_failed_login(self, max_attempts: int = 5, lock_minutes: int = 15) -> None:
        self.login_attempts += 1
        if self.login_attempts >= max_attempts:
            from datetime import timedelta

            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)

    def reset_login_attempts(self) -> None:
        self.login_attempts = 0
        self.locked_until = None
