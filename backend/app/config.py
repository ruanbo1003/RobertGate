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

    # LLM (OpenAI-compatible: SiliconFlow / OpenRouter / 智谱 / OpenAI 等)
    # 默认走 SiliconFlow DeepSeek-V3，可通过 .env.local 覆盖。
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_MODEL: str = "deepseek-ai/DeepSeek-V3"

    # 文生图（默认 SiliconFlow Kolors，走 OpenAI 兼容的 /images/generations）
    T2I_MODEL: str = "Kwai-Kolors/Kolors"
    T2I_SIZE: str = "1024x1024"

    # 法律咨询 RAG（复用 LLM_API_KEY / LLM_BASE_URL；未配 Key 时走 Mock）
    LEGAL_CHAT_MODEL: str = "deepseek-ai/DeepSeek-V3"
    LEGAL_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    LEGAL_PDF_PATH: str = "../data/law/中华人民共和国民法典.pdf"
    LEGAL_INDEX_PATH: str = "data/legal_index.json"
    LEGAL_TOP_K: int = 4
    LEGAL_MIN_SCORE: float = 0.35
    LEGAL_CONTEXT_ROUNDS: int = 20

    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{env}"),
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
