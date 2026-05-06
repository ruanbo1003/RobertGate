from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logger import setup_logging
from app.core.middleware import ApiLoggingMiddleware, ErrorHandlerMiddleware
from app.core.setting import get_settings

from app.api.auth.router import router as auth_router
from app.api.gallery.router import router as gallery_router
from app.api.util.router import router as util_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


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

# Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(gallery_router, prefix="/api/v1")
app.include_router(util_router, prefix="/api/v1")
