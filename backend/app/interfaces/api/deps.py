from functools import lru_cache
from pathlib import Path

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports import AIClient
from app.application.services.admin_hanzi_service import AdminHanziService
from app.application.services.auth_service import AuthService
from app.application.services.english_service import EnglishService
from app.application.services.gallery_service import GalleryService
from app.application.services.hanzi_service import HanziService
from app.application.services.t2i_generation import T2IGenerator, fetch_image_bytes
from app.application.services.t2i_service import T2IService
from app.application.services.t2i_task_service import T2ITaskService
from app.application.services.translate_service import TranslateService
from app.config import get_settings
from app.domain.errors import AuthException
from app.infrastructure.ai.factory import get_ai_client
from app.infrastructure.database.session import async_session, get_db
from app.infrastructure.repositories.hanzi_character_repo import HanziCharacterRepo
from app.infrastructure.repositories.hanzi_level_repo import HanziLevelRepo
from app.infrastructure.repositories.hanzi_progress_repo import HanziProgressRepo
from app.infrastructure.repositories.t2i_repo import (
    T2IImageBlobRepo,
    T2IImageRepo,
    T2ITaskRepo,
    T2ITemplateRepo,
)
from app.infrastructure.repositories.user_repo import UserRepo
from app.infrastructure.tasks import AsyncioTaskRunner


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
    auth: AuthService = Depends(get_auth_service),
) -> str:
    await auth.ensure_admin(user_id)
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


@lru_cache
def get_gallery_service() -> GalleryService:
    settings = get_settings()
    photo_dir = Path(settings.PHOTO_DIR)
    return GalleryService(
        photo_dir=photo_dir,
        thumb_dir=photo_dir / "thumbs",
        thumb_width=settings.THUMB_WIDTH,
    )


@lru_cache
def get_task_runner() -> AsyncioTaskRunner:
    return AsyncioTaskRunner()


async def get_t2i_task_service(
    db: AsyncSession = Depends(get_db),
    ai: AIClient = Depends(get_ai_client_dep),
) -> T2ITaskService:
    generator = T2IGenerator(
        session_factory=async_session,
        ai=ai,
        fetch_image=fetch_image_bytes,
        runner=get_task_runner(),
    )
    return T2ITaskService(
        template_repo=T2ITemplateRepo(db),
        task_repo=T2ITaskRepo(db),
        image_repo=T2IImageRepo(db),
        blob_repo=T2IImageBlobRepo(db),
        ai=ai,
        generator=generator,
    )
