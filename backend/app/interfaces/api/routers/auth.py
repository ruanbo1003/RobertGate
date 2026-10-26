from fastapi import APIRouter, Depends

from app.application.services.auth_service import AuthService
from app.interfaces.api.deps import get_auth_service, get_current_user_id
from app.interfaces.api.response import success
from app.interfaces.api.schemas.auth import LoginRequest, RegisterRequest

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


@router.get("/me")
async def me(
    user_id: str = Depends(get_current_user_id),
    service: AuthService = Depends(get_auth_service),
):
    result = await service.get_me(user_id)
    return success(result)


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
