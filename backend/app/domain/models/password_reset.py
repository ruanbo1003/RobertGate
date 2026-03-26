from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone


class PasswordReset:
    """密码重置 token 领域模型"""

    TOKEN_EXPIRY_MINUTES = 30

    def __init__(
        self,
        id: str,
        user_id: str,
        token: str,
        created_at: datetime,
        used: bool = False,
    ) -> None:
        self.id = id
        self.user_id = user_id
        self.token = token
        self.created_at = created_at
        self.used = used

    @staticmethod
    def create(user_id: str) -> PasswordReset:
        import uuid

        return PasswordReset(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token=secrets.token_urlsafe(32),
            created_at=datetime.now(timezone.utc),
        )

    @property
    def is_expired(self) -> bool:
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        expiry = created + timedelta(minutes=self.TOKEN_EXPIRY_MINUTES)
        return datetime.now(timezone.utc) > expiry

    @property
    def is_valid(self) -> bool:
        return not self.used and not self.is_expired

    def mark_used(self) -> None:
        self.used = True
