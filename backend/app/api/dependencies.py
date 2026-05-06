from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repository.password_reset_repo import PasswordResetRepo
from app.repository.user_repo import UserRepo
from app.service.auth_service import AuthService


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        user_repo=UserRepo(db),
        reset_repo=PasswordResetRepo(db),
    )
