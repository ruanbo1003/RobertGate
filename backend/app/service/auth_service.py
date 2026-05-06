from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.core.exceptions import AuthException
from app.core.setting import get_settings
from app.models.password_reset import PasswordReset
from app.models.user import User
from app.repository.password_reset_repo import PasswordResetRepo
from app.repository.user_repo import UserRepo

settings = get_settings()


class AuthService:
    def __init__(self, user_repo: UserRepo, reset_repo: PasswordResetRepo) -> None:
        self.user_repo = user_repo
        self.reset_repo = reset_repo

    # --- Password ---

    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # --- Token ---

    @staticmethod
    def create_access_token(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        return jwt.encode(
            {"sub": user_id, "exp": expire},
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def decode_access_token(token: str) -> str | None:
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            return payload.get("sub")
        except Exception:
            return None

    # --- User logic ---

    @staticmethod
    def is_user_locked(user: User) -> bool:
        if user.locked_until is None:
            return False
        locked = user.locked_until
        if locked.tzinfo is None:
            locked = locked.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < locked

    @staticmethod
    def record_failed_login(
        user: User, max_attempts: int = 5, lock_minutes: int = 15
    ) -> None:
        user.login_attempts += 1
        if user.login_attempts >= max_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=lock_minutes
            )

    @staticmethod
    def reset_login_attempts(user: User) -> None:
        user.login_attempts = 0
        user.locked_until = None

    # --- Reset token logic ---

    @staticmethod
    def is_reset_valid(reset: PasswordReset) -> bool:
        if reset.used:
            return False
        created = reset.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        expiry = created + timedelta(minutes=30)
        return datetime.now(timezone.utc) <= expiry

    # --- Business operations ---

    def _user_dict(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
        }

    def _auth_result(self, user: User) -> dict:
        return {
            "access_token": self.create_access_token(user.id),
            "token_type": "bearer",
            "expires_in": settings.JWT_EXPIRE_HOURS * 3600,
            "user": self._user_dict(user),
        }

    async def register(self, username: str, email: str, password: str) -> dict:
        if await self.user_repo.find_by_username(username):
            raise AuthException(2010, "用户名已被使用")
        if await self.user_repo.find_by_email(email):
            raise AuthException(2011, "邮箱已被注册")

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=self.hash_password(password),
            created_at=datetime.now(timezone.utc),
            login_attempts=0,
        )
        await self.user_repo.save(user)
        return self._auth_result(user)

    async def login(self, email: str, password: str) -> dict:
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise AuthException(1001, "邮箱或密码错误")

        if self.is_user_locked(user):
            raise AuthException(1002, "账号已被锁定，请稍后再试")

        if not self.verify_password(password, user.hashed_password):
            self.record_failed_login(user)
            await self.user_repo.update(user)
            raise AuthException(1001, "邮箱或密码错误")

        self.reset_login_attempts(user)
        await self.user_repo.update(user)
        return self._auth_result(user)

    async def forgot_password(self, email: str) -> str | None:
        user = await self.user_repo.find_by_email(email)
        if not user:
            return None

        reset = PasswordReset(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token=secrets.token_urlsafe(32),
            created_at=datetime.now(timezone.utc),
            used=False,
        )
        await self.reset_repo.save(reset)
        return reset.token

    async def reset_password(self, token: str, password: str) -> None:
        reset = await self.reset_repo.find_by_token(token)
        if not reset or not self.is_reset_valid(reset):
            raise AuthException(1003, "重置链接无效或已过期")

        user = await self.user_repo.find_by_id(reset.user_id)
        if not user:
            raise AuthException(1003, "重置链接无效或已过期")

        user.hashed_password = self.hash_password(password)
        self.reset_login_attempts(user)
        await self.user_repo.update(user)

        reset.used = True
        await self.reset_repo.update(reset)

    async def check_username(self, username: str) -> bool:
        return await self.user_repo.find_by_username(username) is None

    async def check_email(self, email: str) -> bool:
        return await self.user_repo.find_by_email(email) is None
