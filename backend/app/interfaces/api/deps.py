"""组合根：把 infrastructure 的实现装配进 application 的用例。

工厂函数一律只做装配，不含任何业务判断；无状态的实现（哈希器、令牌、
任务运行器、相册 service）用 @lru_cache 做进程内单例。
"""

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
from app.domain.errors import AuthException, codes
from app.domain.repositories.uow import UnitOfWork
from app.infrastructure.ai.factory import get_ai_client
from app.infrastructure.data.english_data import ENGLISH_THEMES
from app.infrastructure.database.session import get_db
from app.infrastructure.repositories.uow import SqlUnitOfWork, new_uow
from app.infrastructure.security.jwt import JoseTokens
from app.infrastructure.security.password import BcryptHasher
from app.infrastructure.tasks import AsyncioTaskRunner

# ---------- 无状态单例 ----------


@lru_cache
def get_password_hasher() -> BcryptHasher:
    return BcryptHasher()


@lru_cache
def get_token_provider() -> JoseTokens:
    return JoseTokens()


@lru_cache
def get_task_runner() -> AsyncioTaskRunner:
    return AsyncioTaskRunner()


@lru_cache
def get_gallery_service() -> GalleryService:
    settings = get_settings()
    photo_dir = Path(settings.PHOTO_DIR)
    return GalleryService(
        photo_dir=photo_dir,
        thumb_dir=photo_dir / "thumbs",
        thumb_width=settings.THUMB_WIDTH,
    )


def get_ai_client_dep() -> AIClient:
    return get_ai_client()


# ---------- 工作单元 ----------


async def get_uow(db: AsyncSession = Depends(get_db)) -> UnitOfWork:
    return SqlUnitOfWork(db)


# ---------- 认证 ----------


async def get_auth_service(uow: UnitOfWork = Depends(get_uow)) -> AuthService:
    return AuthService(uow, get_password_hasher(), get_token_provider())


async def get_current_user_id(
    authorization: str | None = Header(default=None),
) -> str:
    """从 Authorization: Bearer <token> 提取 user_id。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthException(codes.UNAUTHORIZED, "未登录")
    token = authorization.split(" ", 1)[1].strip()
    user_id = get_token_provider().decode(token)
    if not user_id:
        raise AuthException(codes.UNAUTHORIZED, "未登录")
    return user_id


async def require_admin(
    user_id: str = Depends(get_current_user_id),
    auth: AuthService = Depends(get_auth_service),
) -> str:
    await auth.ensure_admin(user_id)
    return user_id


# ---------- 业务 service ----------


async def get_translate_service(
    ai: AIClient = Depends(get_ai_client_dep),
) -> TranslateService:
    return TranslateService(ai=ai)


async def get_hanzi_service(
    uow: UnitOfWork = Depends(get_uow),
    ai: AIClient = Depends(get_ai_client_dep),
) -> HanziService:
    return HanziService(uow=uow, ai=ai)


async def get_admin_hanzi_service(
    uow: UnitOfWork = Depends(get_uow),
    ai: AIClient = Depends(get_ai_client_dep),
) -> AdminHanziService:
    return AdminHanziService(uow=uow, ai=ai)


def get_english_service() -> EnglishService:
    return EnglishService(themes=ENGLISH_THEMES)


async def get_t2i_service(
    ai: AIClient = Depends(get_ai_client_dep),
) -> T2IService:
    return T2IService(ai=ai)


async def get_t2i_task_service(
    uow: UnitOfWork = Depends(get_uow),
    ai: AIClient = Depends(get_ai_client_dep),
) -> T2ITaskService:
    generator = T2IGenerator(new_uow, ai, fetch_image_bytes, get_task_runner())
    return T2ITaskService(uow=uow, generator=generator)
