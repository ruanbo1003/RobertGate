from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.auth import LoginDTO, RegisterDTO, ResetPasswordDTO
from app.application.services.auth_service import AuthError, AuthService
from app.infrastructure.database.config import get_db
from app.infrastructure.repositories.password_reset_repository_impl import (
    PasswordResetRepositoryImpl,
)
from app.infrastructure.repositories.user_repository_impl import UserRepositoryImpl
from app.interfaces.api.response import error, success
from app.interfaces.api.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_auth_service(session: AsyncSession) -> AuthService:
    return AuthService(
        user_repo=UserRepositoryImpl(session),
        reset_repo=PasswordResetRepositoryImpl(session),
    )


@router.post("/register")
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    try:
        result = await service.register(
            RegisterDTO(username=body.username, email=body.email, password=body.password)
        )
    except AuthError as e:
        return error(e.code, e.message)

    return success(
        {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "user": {
                "id": result.user_id,
                "username": result.username,
                "email": result.email,
                "created_at": result.created_at,
            },
        }
    )


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    try:
        result = await service.login(LoginDTO(email=body.email, password=body.password))
    except AuthError as e:
        return error(e.code, e.message)

    return success(
        {
            "access_token": result.access_token,
            "token_type": result.token_type,
            "expires_in": result.expires_in,
            "user": {
                "id": result.user_id,
                "username": result.username,
                "email": result.email,
                "created_at": result.created_at,
            },
        }
    )


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    token = await service.forgot_password(body.email)
    # 无论邮箱是否存在，都返回相同响应
    response = success(message="如果该邮箱已注册，重置链接已发送")
    # 开发环境下返回 token 便于测试
    if token:
        response["data"] = {"reset_token": token}
    return response


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    try:
        await service.reset_password(ResetPasswordDTO(token=body.token, password=body.password))
    except AuthError as e:
        return error(e.code, e.message)

    return success(message="密码重置成功")


@router.get("/check-username/{username}")
async def check_username(username: str, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    available = await service.check_username(username)
    return success({"available": available})


@router.get("/check-email/{email}")
async def check_email(email: str, db: AsyncSession = Depends(get_db)):
    service = _get_auth_service(db)
    available = await service.check_email(email)
    return success({"available": available})
