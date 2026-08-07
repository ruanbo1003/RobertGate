from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthException
from app.repository.hanzi_character_repo import HanziCharacterRepo
from app.repository.hanzi_level_repo import HanziLevelRepo
from app.repository.hanzi_progress_repo import HanziProgressRepo
from app.repository.user_repo import UserRepo
from app.service.admin_hanzi_service import AdminHanziService
from app.service.ai_client import AIClient, get_ai_client
from app.service.auth_service import AuthService
from app.service.english_service import EnglishService
from app.service.hanzi_service import HanziService
from app.service.t2i_service import T2IService
from app.service.translate_service import TranslateService


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(user_repo=UserRepo(db))


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """从 Authorization: Bearer <token> 提取 user_id。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthException(1001, "未登录")
    token = authorization.split(" ", 1)[1].strip()
    user_id = AuthService.decode_access_token(token)
    if not user_id:
        raise AuthException(1001, "未登录")
    return user_id


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> str:
    user = await UserRepo(db).find_by_id(user_id)
    if not user or user.role != "admin":
        raise AuthException(1002, "无权限")
    return user_id


def get_ai_client_dep() -> AIClient:
    return get_ai_client()


async def get_translate_service(
    ai: AIClient = Depends(get_ai_client_dep),
) -> TranslateService:
    return TranslateService(ai=ai)


async def get_hanzi_service(
    db: AsyncSession = Depends(get_db),
    ai: AIClient = Depends(get_ai_client_dep),
) -> HanziService:
    return HanziService(
        level_repo=HanziLevelRepo(db),
        character_repo=HanziCharacterRepo(db),
        progress_repo=HanziProgressRepo(db),
        ai=ai,
    )


async def get_admin_hanzi_service(
    db: AsyncSession = Depends(get_db),
    ai: AIClient = Depends(get_ai_client_dep),
) -> AdminHanziService:
    return AdminHanziService(
        level_repo=HanziLevelRepo(db),
        character_repo=HanziCharacterRepo(db),
        ai=ai,
    )


def get_english_service() -> EnglishService:
    return EnglishService()


async def get_t2i_service(
    ai: AIClient = Depends(get_ai_client_dep),
) -> T2IService:
    return T2IService(ai=ai)
