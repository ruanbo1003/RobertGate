from functools import lru_cache
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


env = os.environ.get("ENV", "local")


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/robertgate"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # JWT
    JWT_SECRET: str = "robertgate-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Gallery
    PHOTO_DIR: str = "/home/ubuntu/photos"
    THUMB_WIDTH: int = 400

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # App
    DEBUG: bool = False

    # LLM (OpenAI-compatible: OpenRouter / 智谱 / DeepSeek / OpenAI 等)
    # 默认走智谱 BigModel，可通过 .env.local 覆盖。
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4/"
    LLM_MODEL: str = "glm-4.6"

    # 文生图（默认智谱 CogView-3-Flash，走 OpenAI 兼容的 /images/generations）
    T2I_MODEL: str = "cogview-3-flash"
    T2I_SIZE: str = "1024x1024"

    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{env}"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
