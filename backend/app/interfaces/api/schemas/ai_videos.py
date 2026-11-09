"""ai-videos 请求 Schema（出参见 application/dto/ai_video.py）。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models.ai_video import AssetKind


class CreateCharacterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    appearance_prompt: str = Field(min_length=1, max_length=1000)
    personality: str | None = Field(default=None, max_length=500)
    voice_desc: str | None = Field(default=None, max_length=200)


class UpdateCharacterRequest(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    appearance_prompt: str | None = Field(default=None, max_length=1000)
    personality: str | None = Field(default=None, max_length=500)
    voice_desc: str | None = Field(default=None, max_length=200)
    cover_image_id: int | None = None


class GenerateCharacterImageRequest(BaseModel):
    model: str = Field(min_length=1)
    prompt: str | None = None


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    synopsis: str = Field(min_length=1, max_length=1000)
    character_ids: list[int] = Field(min_length=1, max_length=4)
    target_duration: int = Field(ge=30, le=120)
    default_models: dict[str, str] | None = None
    tts_voice: str | None = None


class UpdateProjectRequest(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    synopsis: str | None = Field(default=None, max_length=1000)
    default_models: dict[str, str] | None = None
    tts_voice: str | None = None


class GenerateScriptRequest(BaseModel):
    model: str | None = None


class SplitShotsRequest(BaseModel):
    model: str | None = None
    confirm_replace: bool = False


class CreateShotRequest(BaseModel):
    after_shot_id: int | None = None


class DialogueLineIn(BaseModel):
    character_id: int | None = None
    en: str
    zh: str = ""


class UpdateShotRequest(BaseModel):
    dialogue: list[DialogueLineIn] | None = Field(default=None, max_length=4)
    ref_character_ids: list[int] | None = None
    image_prompt: str | None = None
    video_prompt: str | None = Field(default=None, max_length=1000)


class ReorderShotsRequest(BaseModel):
    shot_ids: list[int] = Field(min_length=1)


class GenerateAssetRequest(BaseModel):
    model: str | None = None
    voice: str | None = None


class GenerateAllRequest(BaseModel):
    types: list[AssetKind] = Field(min_length=1)
    scope: str = Field(default="missing", pattern="^(missing|all)$")


class ComposeRequest(BaseModel):
    ignore_stale: bool = False
