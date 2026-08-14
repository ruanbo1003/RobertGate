from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

from app.config import get_settings
from app.domain.errors import AuthException, codes
from app.domain.models.user import User
from app.domain.repositories.uow import UnitOfWork

settings = get_settings()


class AuthService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

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

    # --- Business operations ---

    def _user_dict(self, user: User) -> dict:
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
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
        if await self.uow.users.find_by_username(username):
            raise AuthException(codes.USERNAME_TAKEN, "用户名已被使用")
        if await self.uow.users.find_by_email(email):
            raise AuthException(codes.EMAIL_TAKEN, "邮箱已被注册")

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=self.hash_password(password),
            role="user",
            created_at=datetime.now(timezone.utc),
        )
        self.uow.users.add(user)
        await self.uow.commit()
        return self._auth_result(user)

    async def login(self, email: str, password: str) -> dict:
        user = await self.uow.users.find_by_email(email)
        if not user:
            raise AuthException(codes.UNAUTHORIZED, "邮箱或密码错误")

        if not self.verify_password(password, user.hashed_password):
            raise AuthException(codes.UNAUTHORIZED, "邮箱或密码错误")

        return self._auth_result(user)

    async def get_me(self, user_id: str) -> dict:
        user = await self.uow.users.find_by_id(user_id)
        if not user:
            raise AuthException(codes.UNAUTHORIZED, "未登录")
        return self._user_dict(user)

    async def check_username(self, username: str) -> bool:
        return await self.uow.users.find_by_username(username) is None

    async def check_email(self, email: str) -> bool:
        return await self.uow.users.find_by_email(email) is None

    async def ensure_admin(self, user_id: str) -> None:
        user = await self.uow.users.find_by_id(user_id)
        if not user or user.role != "admin":
            raise AuthException(codes.FORBIDDEN, "无权限")
