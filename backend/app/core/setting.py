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

    model_config = SettingsConfigDict(
        env_file=f".env.{env}",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
