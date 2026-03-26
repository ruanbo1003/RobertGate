from __future__ import annotations

from app.application.dto.auth import AuthResultDTO, LoginDTO, RegisterDTO, ResetPasswordDTO
from app.application.services.password_hasher import hash_password, verify_password
from app.application.services.token_service import create_access_token
from app.domain.models.password_reset import PasswordReset
from app.domain.models.user import User
from app.domain.repositories.password_reset_repository import PasswordResetRepository
from app.domain.repositories.user_repository import UserRepository


class AuthError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message


class AuthService:
    def __init__(
        self,
        user_repo: UserRepository,
        reset_repo: PasswordResetRepository,
    ) -> None:
        self._user_repo = user_repo
        self._reset_repo = reset_repo

    async def register(self, dto: RegisterDTO) -> AuthResultDTO:
        if await self._user_repo.find_by_username(dto.username):
            raise AuthError(2010, "用户名已被使用")

        if await self._user_repo.find_by_email(dto.email):
            raise AuthError(2011, "邮箱已被注册")

        user = User.create(
            username=dto.username,
            email=dto.email,
            hashed_password=hash_password(dto.password),
        )
        await self._user_repo.save(user)

        token = create_access_token(user.id)
        return AuthResultDTO(
            access_token=token,
            user_id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat(),
        )

    async def login(self, dto: LoginDTO) -> AuthResultDTO:
        user = await self._user_repo.find_by_email(dto.email)
        if not user:
            raise AuthError(1001, "邮箱或密码错误")

        if user.is_locked:
            raise AuthError(1002, "账号已被锁定，请稍后再试")

        if not verify_password(dto.password, user.hashed_password):
            user.record_failed_login()
            await self._user_repo.update(user)
            raise AuthError(1001, "邮箱或密码错误")

        user.reset_login_attempts()
        await self._user_repo.update(user)

        token = create_access_token(user.id)
        return AuthResultDTO(
            access_token=token,
            user_id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at.isoformat(),
        )

    async def forgot_password(self, email: str) -> str | None:
        """返回 reset token（实际场景中通过邮件发送，这里直接返回便于测试）"""
        user = await self._user_repo.find_by_email(email)
        if not user:
            return None  # 不暴露邮箱是否存在

        reset = PasswordReset.create(user.id)
        await self._reset_repo.save(reset)
        return reset.token

    async def reset_password(self, dto: ResetPasswordDTO) -> None:
        reset = await self._reset_repo.find_by_token(dto.token)
        if not reset or not reset.is_valid:
            raise AuthError(1003, "重置链接无效或已过期")

        user = await self._user_repo.find_by_id(reset.user_id)
        if not user:
            raise AuthError(1003, "重置链接无效或已过期")

        user.hashed_password = hash_password(dto.password)
        user.reset_login_attempts()
        await self._user_repo.update(user)

        reset.mark_used()
        await self._reset_repo.update(reset)

    async def check_username(self, username: str) -> bool:
        return await self._user_repo.find_by_username(username) is None

    async def check_email(self, email: str) -> bool:
        return await self._user_repo.find_by_email(email) is None
