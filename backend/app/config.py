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

    # AI Videos（英语启蒙短视频工作台）
    # SiliconFlow 侧复用 LLM_API_KEY / LLM_BASE_URL；OpenRouter 侧用独立 Key。
    AV_DATA_DIR: str = "data/ai-videos"
    AV_IMAGE_SIZE: str = "720x1280"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # invest-reports（投资报告 Agent，走 OPENROUTER_API_KEY）
    IR_DATA_DIR: str = "data/invest-reports"
    IR_LLM_MODEL: str = "deepseek/deepseek-v3.2"
    IR_SEARCH_MODEL: str = "deepseek/deepseek-v3.2:online"
    # kie.ai（对白镜音视同出渠道，功能见 docs/superpowers/specs/2026-11-09-av-dialogue-shots-design.md）
    KIE_API_KEY: str = ""
    KIE_BASE_URL: str = "https://api.kie.ai/api/v1"
    KIE_UPLOAD_BASE_URL: str = "https://kieai.redpandaai.co/api"
    # 对白镜（音视同出）主模型 kie.ai / 兜底模型 OpenRouter
    AV_DIALOGUE_MODEL: str = "gemini-omni-video"
    AV_DIALOGUE_FALLBACK_MODEL: str = "bytedance/seedance-2.0-fast"
    AV_WHISPER_MODEL: str = "small"
    # macOS Homebrew 瘦身版 ffmpeg 无 subtitles 滤镜（libass），烧字幕需指向
    # ffmpeg-full（如 /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg）
    AV_FFMPEG_BIN: str = "ffmpeg"
    AV_FFPROBE_BIN: str = "ffprobe"
    # TTS 语速后处理（ffmpeg atempo）：1.0 不变，0.85~0.95 适合启蒙儿童
    AV_TTS_TEMPO: float = 1.0

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
