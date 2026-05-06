from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service
from app.core.response import success
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(
    body: RegisterRequest, service: AuthService = Depends(get_auth_service)
):
    result = await service.register(body.username, body.email, body.password)
    return success(result)


@router.post("/login")
async def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    result = await service.login(body.email, body.password)
    return success(result)


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest, service: AuthService = Depends(get_auth_service)
):
    token = await service.forgot_password(body.email)
    data = {"reset_token": token} if token else None
    return success(data=data, message="如果该邮箱已注册，重置链接已发送")


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest, service: AuthService = Depends(get_auth_service)
):
    await service.reset_password(body.token, body.password)
    return success(message="密码重置成功")


@router.get("/check-username/{username}")
async def check_username(
    username: str, service: AuthService = Depends(get_auth_service)
):
    available = await service.check_username(username)
    return success({"available": available})


@router.get("/check-email/{email}")
async def check_email(email: str, service: AuthService = Depends(get_auth_service)):
    available = await service.check_email(email)
    return success({"available": available})
