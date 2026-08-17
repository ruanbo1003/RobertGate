from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.application.dto.auth import AuthResult, UserOut
from app.application.ports import PasswordHasher, TokenProvider
from app.domain.errors import AuthException, codes
from app.domain.models.user import User
from app.domain.repositories.uow import UnitOfWork


class AuthService:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        tokens: TokenProvider,
    ) -> None:
        self.uow = uow
        self.hasher = hasher
        self.tokens = tokens

    # --- Business operations ---

    def _auth_result(self, user: User) -> AuthResult:
        return AuthResult(
            access_token=self.tokens.create(user.id),
            token_type="bearer",
            expires_in=self.tokens.ttl_seconds,
            user=UserOut.model_validate(user),
        )

    async def register(self, username: str, email: str, password: str) -> AuthResult:
        if await self.uow.users.find_by_username(username):
            raise AuthException(codes.USERNAME_TAKEN, "用户名已被使用")
        if await self.uow.users.find_by_email(email):
            raise AuthException(codes.EMAIL_TAKEN, "邮箱已被注册")

        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            hashed_password=self.hasher.hash(password),
            role="user",
            created_at=datetime.now(timezone.utc),
        )
        self.uow.users.add(user)
        await self.uow.commit()
        return self._auth_result(user)

    async def login(self, email: str, password: str) -> AuthResult:
        user = await self.uow.users.find_by_email(email)
        if not user:
            raise AuthException(codes.UNAUTHORIZED, "邮箱或密码错误")

        if not self.hasher.verify(password, user.hashed_password):
            raise AuthException(codes.UNAUTHORIZED, "邮箱或密码错误")

        return self._auth_result(user)

    async def get_me(self, user_id: str) -> UserOut:
        user = await self.uow.users.find_by_id(user_id)
        if not user:
            raise AuthException(codes.UNAUTHORIZED, "未登录")
        return UserOut.model_validate(user)

    async def check_username(self, username: str) -> bool:
        return await self.uow.users.find_by_username(username) is None

    async def check_email(self, email: str) -> bool:
        return await self.uow.users.find_by_email(email) is None

    async def ensure_admin(self, user_id: str) -> None:
        user = await self.uow.users.find_by_id(user_id)
        if not user or not user.is_admin:
            raise AuthException(codes.FORBIDDEN, "无权限")
