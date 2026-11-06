"""AI Videos（英语启蒙短视频工作台）领域模型。

实体：角色（含候选设定图）、项目、分镜。分镜上图/视频/配音三类产物各自
持有一组扁平列（state/path/model/stale/error/version），状态机与过期链
不变量收在 AvShot 的方法里；拆分镜 / 时长估算 / 状态聚合为纯函数。
对应 docs/api/ai-videos.md 与 docs/prd/ai-videos.md。
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.errors import ParamException, codes
from app.domain.models.base import Base

TITLE_MAX = 100
SYNOPSIS_MAX = 1000
NAME_MAX = 50
PROMPT_MAX = 1000
PERSONALITY_MAX = 500
DURATION_MIN = 30
DURATION_MAX = 120
CANDIDATE_IMAGES_MAX = 8

MODEL_TYPES = ("llm", "t2i", "i2v", "tts")


class AssetKind(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class AssetState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class ComposeState(StrEnum):
    NONE = "none"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _require_text(value: str | None, field: str, max_len: int) -> str:
    value = (value or "").strip()
    if not value:
        raise ParamException(codes.AV_PARAM_INVALID, f"{field} 不能为空")
    if len(value) > max_len:
        raise ParamException(codes.AV_PARAM_INVALID, f"{field} 超长（最大 {max_len} 字符）")
    return value


# ---------------- 角色 ----------------


class AvCharacter(Base):
    __tablename__ = "av_characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX), unique=True, index=True)
    appearance_prompt: Mapped[str] = mapped_column(Text)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(cls, name: str, appearance_prompt: str, personality: str | None) -> AvCharacter:
        now = _now()
        return cls(
            name=_require_text(name, "角色名称", NAME_MAX),
            appearance_prompt=_require_text(appearance_prompt, "外形描述", PROMPT_MAX),
            personality=((personality or "").strip() or None),
            cover_image_id=None,
            created_at=now,
            updated_at=now,
        )

    def apply_update(
        self,
        name: str | None,
        appearance_prompt: str | None,
        personality: str | None,
    ) -> None:
        if name is not None:
            self.name = _require_text(name, "角色名称", NAME_MAX)
        if appearance_prompt is not None:
            self.appearance_prompt = _require_text(appearance_prompt, "外形描述", PROMPT_MAX)
        if personality is not None:
            personality = personality.strip()
            if len(personality) > PERSONALITY_MAX:
                raise ParamException(
                    codes.AV_PARAM_INVALID, f"性格设定超长（最大 {PERSONALITY_MAX} 字符）"
                )
            self.personality = personality or None
        self.updated_at = _now()

    def touch(self) -> None:
        self.updated_at = _now()


class AvCharacterImage(Base):
    __tablename__ = "av_character_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("av_characters.id", ondelete="CASCADE"), index=True
    )
    path: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(cls, character_id: int, path: str) -> AvCharacterImage:
        return cls(character_id=character_id, path=path, created_at=_now())


# ---------------- 项目 ----------------


def _validate_models(models: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in MODEL_TYPES:
        value = (models or {}).get(key)
        if not value or not isinstance(value, str):
            raise ParamException(codes.AV_PARAM_INVALID, f"default_models.{key} 不能为空")
        out[key] = value
    return out


class AvProject(Base):
    __tablename__ = "av_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX))
    synopsis: Mapped[str] = mapped_column(Text)
    target_duration: Mapped[int] = mapped_column(Integer)
    default_models: Mapped[dict] = mapped_column(JSONB)
    tts_voice: Mapped[str] = mapped_column(String(64))
    script: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    compose_state: Mapped[str] = mapped_column(String(16), default=ComposeState.NONE)
    compose_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    compose_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    compose_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(
        cls,
        title: str,
        synopsis: str,
        target_duration: int,
        default_models: dict[str, str],
        tts_voice: str,
    ) -> AvProject:
        if not (DURATION_MIN <= target_duration <= DURATION_MAX):
            raise ParamException(
                codes.AV_PARAM_INVALID,
                f"目标时长须在 {DURATION_MIN}-{DURATION_MAX} 秒之间",
            )
        now = _now()
        return cls(
            title=_require_text(title, "标题", TITLE_MAX),
            synopsis=_require_text(synopsis, "故事梗概", SYNOPSIS_MAX),
            target_duration=target_duration,
            default_models=_validate_models(default_models),
            tts_voice=_require_text(tts_voice, "配音音色", 64),
            script=None,
            compose_state=ComposeState.NONE,
            compose_path=None,
            compose_error=None,
            compose_stale=False,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        self.updated_at = _now()

    def set_script(self, script: dict) -> None:
        self.script = validate_script(script)
        self.touch()

    def mark_compose_running(self) -> None:
        self.compose_state = ComposeState.RUNNING
        self.compose_path = None
        self.compose_error = None
        self.compose_stale = False
        self.touch()

    def mark_compose_succeeded(self, path: str) -> None:
        self.compose_state = ComposeState.SUCCESS
        self.compose_path = path
        self.compose_error = None
        self.compose_stale = False
        self.touch()

    def mark_compose_failed(self, error: str) -> None:
        self.compose_state = ComposeState.FAILED
        self.compose_error = error
        self.touch()

    def mark_compose_stale(self) -> None:
        if self.compose_state == ComposeState.SUCCESS:
            self.compose_stale = True


class AvProjectCharacter(Base):
    """项目-角色关联（用于 used_count 与删除保护）。"""

    __tablename__ = "av_project_characters"

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("av_projects.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("av_characters.id", ondelete="RESTRICT"), primary_key=True
    )


# ---------------- 分镜 ----------------

# 过期链：上游字段 -> 受影响产物
_STALE_TRIGGERS: dict[str, tuple[AssetKind, ...]] = {
    "image_prompt": (AssetKind.IMAGE, AssetKind.VIDEO),
    "ref_character_ids": (AssetKind.IMAGE, AssetKind.VIDEO),
    "video_prompt": (AssetKind.VIDEO,),
    "line_en": (AssetKind.AUDIO,),
    "speaker_character_id": (AssetKind.AUDIO,),
}

_PATCHABLE_FIELDS = (
    "line_en",
    "line_zh",
    "speaker_character_id",
    "ref_character_ids",
    "image_prompt",
    "video_prompt",
    "duration_estimate",
)


class AvShot(Base):
    __tablename__ = "av_shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("av_projects.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    duration_estimate: Mapped[float] = mapped_column(Float, default=5.0)
    speaker_character_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 出场角色 id 列表（有序，次序即生成时参考图点名次序）
    ref_character_ids: Mapped[list] = mapped_column(JSONB, default=list)
    line_en: Mapped[str] = mapped_column(Text, default="")
    line_zh: Mapped[str] = mapped_column(Text, default="")
    image_prompt: Mapped[str] = mapped_column(Text, default="")
    # 图生视频提示：角色动作 + 运镜 + 氛围；为空时回退 image_prompt
    video_prompt: Mapped[str] = mapped_column(Text, default="")

    image_state: Mapped[str] = mapped_column(String(16), default=AssetState.PENDING)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    image_model: Mapped[str] = mapped_column(String(128), default="")
    image_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    image_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_version: Mapped[int] = mapped_column(Integer, default=0)

    video_state: Mapped[str] = mapped_column(String(16), default=AssetState.PENDING)
    video_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_model: Mapped[str] = mapped_column(String(128), default="")
    video_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    video_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_version: Mapped[int] = mapped_column(Integer, default=0)

    audio_state: Mapped[str] = mapped_column(String(16), default=AssetState.PENDING)
    audio_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_model: Mapped[str] = mapped_column(String(128), default="")
    audio_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_version: Mapped[int] = mapped_column(Integer, default=0)
    audio_voice: Mapped[str] = mapped_column(String(64), default="")
    audio_duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def create(
        cls,
        project_id: int,
        order_index: int,
        speaker_character_id: int | None,
        ref_character_ids: list[int],
        line_en: str,
        line_zh: str,
        image_prompt: str,
        models: dict[str, str],
        tts_voice: str,
        video_prompt: str = "",
    ) -> AvShot:
        now = _now()
        return cls(
            project_id=project_id,
            order_index=order_index,
            duration_estimate=estimate_duration(line_en),
            speaker_character_id=speaker_character_id,
            ref_character_ids=list(ref_character_ids),
            line_en=line_en,
            line_zh=line_zh,
            image_prompt=image_prompt,
            video_prompt=video_prompt,
            image_state=AssetState.PENDING,
            image_model=models["t2i"],
            image_stale=False,
            image_version=0,
            video_state=AssetState.PENDING,
            video_model=models["i2v"],
            video_stale=False,
            video_version=0,
            audio_state=AssetState.PENDING,
            audio_model=models["tts"],
            audio_stale=False,
            audio_version=0,
            audio_voice=tts_voice,
            audio_duration=None,
            created_at=now,
            updated_at=now,
        )

    # ---- 按产物类型读写扁平列 ----

    def asset_state(self, kind: AssetKind) -> AssetState:
        return AssetState(getattr(self, f"{kind.value}_state"))

    def asset_path(self, kind: AssetKind) -> str | None:
        return getattr(self, f"{kind.value}_path")

    def asset_stale(self, kind: AssetKind) -> bool:
        return getattr(self, f"{kind.value}_stale")

    def asset_error(self, kind: AssetKind) -> str | None:
        return getattr(self, f"{kind.value}_error")

    def asset_version(self, kind: AssetKind) -> int:
        return getattr(self, f"{kind.value}_version")

    def asset_model(self, kind: AssetKind) -> str:
        return getattr(self, f"{kind.value}_model")

    def _set(self, kind: AssetKind, field: str, value: object) -> None:
        setattr(self, f"{kind.value}_{field}", value)

    # ---- 状态机 ----

    def ensure_not_busy(self, kind: AssetKind) -> None:
        if self.asset_state(kind) == AssetState.RUNNING:
            raise ParamException(codes.AV_ASSET_BUSY, "该产物正在生成中")

    def mark_pending(self, kind: AssetKind, model: str, voice: str | None = None) -> None:
        self.ensure_not_busy(kind)
        self._set(kind, "state", AssetState.PENDING)
        self._set(kind, "model", model)
        self._set(kind, "error", None)
        if kind == AssetKind.AUDIO and voice:
            self.audio_voice = voice
        self.updated_at = _now()

    def mark_running(self, kind: AssetKind) -> None:
        self._set(kind, "state", AssetState.RUNNING)
        self._set(kind, "error", None)
        self.updated_at = _now()

    def mark_succeeded(
        self, kind: AssetKind, path: str, audio_duration: float | None = None
    ) -> None:
        self._set(kind, "state", AssetState.SUCCESS)
        self._set(kind, "path", path)
        self._set(kind, "error", None)
        self._set(kind, "stale", False)
        self._set(kind, "version", self.asset_version(kind) + 1)
        if kind == AssetKind.AUDIO and audio_duration is not None:
            self.audio_duration = audio_duration
        self.updated_at = _now()

    def mark_failed(self, kind: AssetKind, error: str) -> None:
        self._set(kind, "state", AssetState.FAILED)
        self._set(kind, "error", error)
        self.updated_at = _now()

    # ---- 过期链 ----

    def apply_patch(self, **fields: Any) -> list[AssetKind]:
        """应用编辑并返回被标记过期的产物类型（只有 success 态产物会被标 stale）。"""
        unknown = set(fields) - set(_PATCHABLE_FIELDS)
        if unknown:
            raise ParamException(codes.AV_PARAM_INVALID, f"不支持的字段：{sorted(unknown)}")
        staled: set[AssetKind] = set()
        for field, value in fields.items():
            if getattr(self, field) == value:
                continue
            setattr(self, field, value)
            for kind in _STALE_TRIGGERS.get(field, ()):
                if self.asset_state(kind) == AssetState.SUCCESS:
                    self._set(kind, "stale", True)
                    staled.add(kind)
        if fields:
            self.updated_at = _now()
        return sorted(staled, key=lambda k: k.value)


# ---------------- 剧本 ----------------


def validate_script(script: Any) -> dict:
    """校验并规范化剧本结构：{scenes: [{setting, lines: [{character_id, en, zh}]}]}。"""
    if not isinstance(script, dict):
        raise ParamException(codes.AV_PARAM_INVALID, "剧本必须是对象")
    scenes_raw = script.get("scenes")
    if not isinstance(scenes_raw, list) or not scenes_raw:
        raise ParamException(codes.AV_PARAM_INVALID, "剧本至少包含一个场景")
    scenes: list[dict] = []
    for scene in scenes_raw:
        if not isinstance(scene, dict):
            raise ParamException(codes.AV_PARAM_INVALID, "场景必须是对象")
        setting = str(scene.get("setting") or "").strip()
        lines_raw = scene.get("lines")
        if not isinstance(lines_raw, list) or not lines_raw:
            raise ParamException(codes.AV_PARAM_INVALID, "场景至少包含一句对白")
        lines: list[dict] = []
        for line in lines_raw:
            if not isinstance(line, dict):
                raise ParamException(codes.AV_PARAM_INVALID, "对白必须是对象")
            character_id = line.get("character_id")
            if not isinstance(character_id, int):
                raise ParamException(codes.AV_PARAM_INVALID, "对白缺少 character_id")
            en = str(line.get("en") or "").strip()
            if not en:
                raise ParamException(codes.AV_PARAM_INVALID, "对白缺少英文台词")
            zh = str(line.get("zh") or "").strip()
            video_prompt = str(line.get("video_prompt") or "").strip()
            image_prompt = str(line.get("image_prompt") or "").strip()
            characters_raw = line.get("characters")
            characters = (
                [str(c).strip() for c in characters_raw if str(c).strip()]
                if isinstance(characters_raw, list)
                else []
            )
            lines.append(
                {
                    "character_id": character_id,
                    "en": en,
                    "zh": zh,
                    "image_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "characters": characters,
                }
            )
        scenes.append({"setting": setting, "lines": lines})
    return {"scenes": scenes}


def estimate_duration(line_en: str) -> float:
    """按台词词数估算分镜时长（秒），clamp 到 3-6s（单段 i2v 的常规长度）。"""
    words = len([w for w in line_en.split() if w])
    return round(min(6.0, max(3.0, words * 0.45 + 1.5)), 1)


def shots_from_script(
    project_id: int,
    script: dict,
    models: dict[str, str],
    tts_voice: str,
    resolve_character: Callable[[str], int | None],
) -> list[AvShot]:
    """把剧本拆成分镜：每句对白一镜。

    画面 prompt：优先用 LLM 按句产出的 line.image_prompt（纯场景/构图描述）；
    缺省回退"场景 + 台词"拼接。两者都不含角色外形——外形与参考图由生成队列
    按模型能力动态注入（multi 档参考图点名 / none 档拼外形描述），避免把
    设定图类指令带进分镜画面。
    出场角色：line.characters 逐名经 resolve_character 解析（解析不到的忽略），
    去重保序；为空则回退 [speaker_id]。video_prompt 直落（缺省为空串）。
    """
    script = validate_script(script)
    shots: list[AvShot] = []
    order = 1
    for scene in script["scenes"]:
        setting = scene["setting"]
        for line in scene["lines"]:
            speaker_id = line["character_id"]
            ref_ids: list[int] = []
            for name in line["characters"]:
                cid = resolve_character(name)
                if cid is not None and cid not in ref_ids:
                    ref_ids.append(cid)
            if not ref_ids and speaker_id is not None:
                ref_ids = [speaker_id]
            prompt = line["image_prompt"] or (
                f"{setting}, {line['en']} "
                "children picture book style, soft lighting, vertical 9:16"
            )
            shots.append(
                AvShot.create(
                    project_id=project_id,
                    order_index=order,
                    speaker_character_id=speaker_id,
                    ref_character_ids=ref_ids,
                    line_en=line["en"],
                    line_zh=line["zh"],
                    image_prompt=prompt,
                    video_prompt=line["video_prompt"],
                    models=models,
                    tts_voice=tts_voice,
                )
            )
            order += 1
    return shots


# ---------------- 聚合与合成校验 ----------------


def derive_project_status(shots: list[AvShot], queue_active: bool) -> str:
    if not shots:
        return "draft"
    states = [s.asset_state(kind) for s in shots for kind in AssetKind]
    if queue_active or AssetState.RUNNING in states:
        return "generating"
    if AssetState.FAILED in states:
        return "partial_failed"
    if all(st == AssetState.SUCCESS for st in states):
        return "completed"
    return "draft"


def missing_compose_items(shots: list[AvShot]) -> list[dict]:
    """合成前置校验：video/audio 必须全部 success（字幕随台词烧录，不依赖 image）。"""
    return [
        {"shot_id": s.id, "shot_order": s.order_index, "kind": kind.value}
        for s in shots
        for kind in (AssetKind.VIDEO, AssetKind.AUDIO)
        if s.asset_state(kind) != AssetState.SUCCESS
    ]


def stale_items(shots: list[AvShot]) -> list[dict]:
    return [
        {"shot_id": s.id, "shot_order": s.order_index, "kind": kind.value}
        for s in shots
        for kind in AssetKind
        if s.asset_stale(kind)
    ]
