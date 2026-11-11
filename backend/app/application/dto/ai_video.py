"""ai-videos 出参 DTO。

产物文件 URL 统一拼 `GET /api/v1/ai-videos/files/{path}`，与路由一一对应。
"""

from __future__ import annotations

from app.application.dto.base import DTO, IsoDt
from app.domain.models.ai_video import (
    AssetKind,
    AvCharacter,
    AvCharacterImage,
    AvProject,
    AvShot,
    derive_project_status,
)

FILE_URL_PREFIX = "/api/v1/ai-videos/files"


def file_url(path: str | None) -> str | None:
    return f"{FILE_URL_PREFIX}/{path}" if path else None


class CandidateImageOut(DTO):
    id: int | None
    url: str

    @classmethod
    def build(cls, image: AvCharacterImage) -> CandidateImageOut:
        return cls(id=image.id, url=file_url(image.path) or "")


class CharacterOut(DTO):
    id: int
    name: str
    appearance_prompt: str
    personality: str | None
    voice_desc: str
    cover_image_url: str | None
    candidate_images: list[CandidateImageOut]
    used_count: int
    created_at: IsoDt
    updated_at: IsoDt

    @classmethod
    def build(
        cls,
        char: AvCharacter,
        images: list[AvCharacterImage],
        used_count: int,
    ) -> CharacterOut:
        cover = next((i for i in images if i.id == char.cover_image_id), None)
        return cls(
            id=char.id,
            name=char.name,
            appearance_prompt=char.appearance_prompt,
            personality=char.personality,
            voice_desc=char.voice_desc,
            cover_image_url=file_url(cover.path) if cover else None,
            candidate_images=[CandidateImageOut.build(i) for i in images],
            used_count=used_count,
            created_at=char.created_at,
            updated_at=char.updated_at,
        )


class CharacterRefOut(DTO):
    id: int
    name: str
    cover_image_url: str | None


class GeneratedImageOut(DTO):
    id: int | None
    url: str


class AssetOut(DTO):
    state: str
    url: str | None
    model: str
    stale: bool
    error: str | None
    version: int


class AudioAssetOut(AssetOut):
    voice: str
    duration: float | None


class DialogueLineOut(DTO):
    character_id: int | None
    en: str
    zh: str


def _asset_out(shot: AvShot, kind: AssetKind) -> AssetOut:
    return AssetOut(
        state=shot.asset_state(kind).value,
        url=file_url(shot.asset_path(kind)),
        model=shot.asset_model(kind),
        stale=shot.asset_stale(kind),
        error=shot.asset_error(kind),
        version=shot.asset_version(kind),
    )


class ShotOut(DTO):
    id: int | None
    order: int
    duration_estimate: float
    ref_character_ids: list[int]
    video_prompt: str
    image_prompt: str
    dialogue: list[DialogueLineOut]
    image: AssetOut
    video: AssetOut
    audio: AudioAssetOut | None

    @classmethod
    def build(cls, shot: AvShot) -> ShotOut:
        audio_out: AudioAssetOut | None = None
        if not shot.has_dialogue:
            base = _asset_out(shot, AssetKind.AUDIO)
            audio_out = AudioAssetOut(
                **base.model_dump(), voice=shot.audio_voice, duration=shot.audio_duration
            )
        return cls(
            id=shot.id,
            order=shot.order_index,
            duration_estimate=shot.duration_estimate,
            ref_character_ids=list(shot.ref_character_ids),
            video_prompt=shot.video_prompt,
            image_prompt=shot.image_prompt,
            dialogue=[DialogueLineOut(**ln) for ln in shot.dialogue],
            image=_asset_out(shot, AssetKind.IMAGE),
            video=_asset_out(shot, AssetKind.VIDEO),
            audio=audio_out,
        )


class ComposeOut(DTO):
    state: str
    video_url: str | None
    error: str | None
    stale: bool

    @classmethod
    def build(cls, project: AvProject) -> ComposeOut:
        return cls(
            state=project.compose_state,
            video_url=file_url(project.compose_path),
            error=project.compose_error,
            stale=project.compose_stale,
        )


class ProgressOut(DTO):
    done: int
    total: int


class ProjectSummaryOut(DTO):
    id: int
    title: str
    status: str
    cover_url: str | None
    duration_estimate: int
    shot_count: int
    progress: dict[str, int]
    updated_at: IsoDt

    @classmethod
    def build(cls, project: AvProject, shots: list[AvShot], queue_active: bool) -> ProjectSummaryOut:
        cover = next((s.image_path for s in shots if s.image_path), None)
        return cls(
            id=project.id,
            title=project.title,
            status=derive_project_status(shots, queue_active),
            cover_url=file_url(cover),
            duration_estimate=round(sum(s.duration_estimate for s in shots)),
            shot_count=len(shots),
            progress={
                kind.value: sum(
                    1 for s in shots if s.asset_state(kind).value == "success"
                )
                for kind in AssetKind
            },
            updated_at=project.updated_at,
        )


class ProjectDetailOut(DTO):
    id: int
    title: str
    synopsis: str
    status: str
    target_duration: int
    characters: list[CharacterRefOut]
    default_models: dict[str, str]
    tts_voice: str
    script: dict | None
    compose: ComposeOut
    shots: list[ShotOut]


class QueueOut(DTO):
    pending: int
    running: int
    paused: bool
    paused_reason: str | None


class AssetStatusLiteOut(DTO):
    state: str
    stale: bool
    url: str | None
    version: int
    error: str | None
    duration: float | None = None


class ShotStatusOut(DTO):
    id: int
    image: AssetStatusLiteOut
    video: AssetStatusLiteOut
    audio: AssetStatusLiteOut | None

    @classmethod
    def build(cls, shot: AvShot) -> ShotStatusOut:
        def lite(kind: AssetKind, duration: float | None = None) -> AssetStatusLiteOut:
            return AssetStatusLiteOut(
                state=shot.asset_state(kind).value,
                stale=shot.asset_stale(kind),
                url=file_url(shot.asset_path(kind)),
                version=shot.asset_version(kind),
                error=shot.asset_error(kind),
                duration=duration,
            )

        return cls(
            id=shot.id,
            image=lite(AssetKind.IMAGE),
            video=lite(AssetKind.VIDEO),
            audio=None if shot.has_dialogue else lite(AssetKind.AUDIO, shot.audio_duration),
        )


class ProjectStatusOut(DTO):
    status: str
    queue: QueueOut
    progress: dict[str, ProgressOut]
    stale_count: int
    compose: ComposeOut
    shots: list[ShotStatusOut]
