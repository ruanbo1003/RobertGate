from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.infrastructure.database.migrate import run_migrations, wait_for_db
from app.infrastructure.logging import setup_logging
from app.interfaces.api.middleware import ApiLoggingMiddleware, ErrorHandlerMiddleware

from app.interfaces.api.routers.admin_hanzi import router as admin_hanzi_router
from app.interfaces.api.routers.ai_tools import router as ai_tools_router
from app.interfaces.api.routers.t2i import router as t2i_router
from app.interfaces.api.routers.auth import router as auth_router
from app.interfaces.api.routers.gallery import router as gallery_router
from app.interfaces.api.routers.hanzi import router as hanzi_router
from app.interfaces.api.routers.util import router as util_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await wait_for_db()
    await run_migrations()
    yield


ROUTERS: list[tuple[APIRouter, str]] = [
    (auth_router, "/api/v1"),
    (gallery_router, "/api/v1"),
    (ai_tools_router, "/api/v1"),
    (t2i_router, "/api/v1"),
    (hanzi_router, "/api/v1"),
    (admin_hanzi_router, "/api/v1"),
    (util_router, "/api"),
]


def create_app() -> FastAPI:
    app = FastAPI(title="RobertGate API", version="0.2.0", lifespan=lifespan)

    # Middleware (last added = first executed)
    app.add_middleware(ApiLoggingMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router, prefix in ROUTERS:
        app.include_router(router, prefix=prefix)

    return app


app = create_app()
