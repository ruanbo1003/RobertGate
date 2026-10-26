"""python-jose 令牌实现（原 AuthService 的静态方法，逻辑原样搬运）。

payload 结构 `{"sub": user_id, "exp": ...}`、算法与过期时间均从 settings 读，
与重构前逐字一致。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import get_settings


class JoseTokens:
    def __init__(self) -> None:
        settings = get_settings()
        self._secret = settings.JWT_SECRET
        self._algorithm = settings.JWT_ALGORITHM
        self._expire_hours = settings.JWT_EXPIRE_HOURS

    @property
    def ttl_seconds(self) -> int:
        return self._expire_hours * 3600

    def create(self, user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(hours=self._expire_hours)
        return jwt.encode(
            {"sub": user_id, "exp": expire},
            self._secret,
            algorithm=self._algorithm,
        )

    def decode(self, token: str) -> str | None:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
            return payload.get("sub")
        except Exception:
            return None
