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
VOICE_DESC_MAX = 200
DIALOGUE_LINES_MAX = 4
# 单镜台词总时长上限（秒）：对白镜合并的贪心约束，也是音视同出模型最大档位
DIALOGUE_SECONDS_MAX = 10.0

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
    # 音色气质描述（对白镜 prompt 用），如"清脆的小女孩声"；空串 = 未设置
    voice_desc: Mapped[str] = mapped_column(String(VOICE_DESC_MAX), default="")
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
            voice_desc="",
            cover_image_id=None,
            created_at=now,
            updated_at=now,
        )

    def apply_update(
        self,
        name: str | None,
        appearance_prompt: str | None,
        personality: str | None,
        voice_desc: str | None = None,
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
        if voice_desc is not None:
            voice_desc = voice_desc.strip()
            if len(voice_desc) > VOICE_DESC_MAX:
                raise ParamException(
                    codes.AV_PARAM_INVALID, f"音色描述超长（最大 {VOICE_DESC_MAX} 字符）"
                )
            self.voice_desc = voice_desc
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
    "dialogue": (AssetKind.VIDEO,),
}

_PATCHABLE_FIELDS = (
    "dialogue",
    "ref_character_ids",
    "image_prompt",
    "video_prompt",
    "duration_estimate",
)


def validate_dialogue(value: Any) -> list[dict]:
    """校验并规范化台词列表：[{character_id: int|None, en, zh}]，最多 4 条。"""
    if not isinstance(value, list):
        raise ParamException(codes.AV_PARAM_INVALID, "台词必须是列表")
    if len(value) > DIALOGUE_LINES_MAX:
        raise ParamException(
            codes.AV_PARAM_INVALID, f"单镜台词最多 {DIALOGUE_LINES_MAX} 句"
        )
    out: list[dict] = []
    for line in value:
        if not isinstance(line, dict):
            raise ParamException(codes.AV_PARAM_INVALID, "台词必须是对象")
        character_id = line.get("character_id")
        if character_id is not None and not isinstance(character_id, int):
            raise ParamException(codes.AV_PARAM_INVALID, "台词 character_id 必须是整数或空")
        en = str(line.get("en") or "").strip()
        if not en:
            raise ParamException(codes.AV_PARAM_INVALID, "台词缺少英文内容")
        zh = str(line.get("zh") or "").strip()
        out.append({"character_id": character_id, "en": en, "zh": zh})
    return out


def _raw_dialogue_seconds(dialogue: list[dict]) -> float:
    words = sum(len([w for w in line["en"].split() if w]) for line in dialogue)
    return words * 0.45 + 1.5


def estimate_dialogue_duration(dialogue: list[dict]) -> float:
    """按台词总词数估算对白镜时长（秒），clamp 3-10（音视同出模型最大档位）。"""
    return round(min(DIALOGUE_SECONDS_MAX, max(3.0, _raw_dialogue_seconds(dialogue))), 1)


class AvShot(Base):
    __tablename__ = "av_shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("av_projects.id", ondelete="CASCADE"), index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    duration_estimate: Mapped[float] = mapped_column(Float, default=5.0)
    # 旧单台词三字段：0010 回填进 dialogue 后冻结，新代码不再读写
    speaker_character_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 出场角色 id 列表（有序，次序即生成时参考图点名次序）
    ref_character_ids: Mapped[list] = mapped_column(JSONB, default=list)
    line_en: Mapped[str] = mapped_column(Text, default="")
    line_zh: Mapped[str] = mapped_column(Text, default="")
    # 台词列表 [{character_id: int|None, en, zh}]；非空 = 说话镜（音视同出），空 = 纯画面镜
    dialogue: Mapped[list] = mapped_column(JSONB, default=list)
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
        ref_character_ids: list[int],
        dialogue: list[dict],
        image_prompt: str,
        models: dict[str, str],
        tts_voice: str,
        video_prompt: str = "",
    ) -> AvShot:
        now = _now()
        dialogue = validate_dialogue(dialogue)
        return cls(
            project_id=project_id,
            order_index=order_index,
            duration_estimate=estimate_dialogue_duration(dialogue),
            speaker_character_id=None,
            ref_character_ids=list(ref_character_ids),
            line_en="",
            line_zh="",
            dialogue=dialogue,
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

    @property
    def has_dialogue(self) -> bool:
        return bool(self.dialogue)

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
        if "dialogue" in fields:
            fields["dialogue"] = validate_dialogue(fields["dialogue"])
        staled: set[AssetKind] = set()
        dialogue_changed = False
        for field, value in fields.items():
            if getattr(self, field) == value:
                continue
            setattr(self, field, value)
            if field == "dialogue":
                dialogue_changed = True
            for kind in _STALE_TRIGGERS.get(field, ()):
                if self.asset_state(kind) == AssetState.SUCCESS:
                    self._set(kind, "stale", True)
                    staled.add(kind)
        if dialogue_changed:
            # 台词变更后重估时长（显式传入的 duration_estimate 会被覆盖）
            self.duration_estimate = estimate_dialogue_duration(self.dialogue)
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


def group_script_into_shots(script: dict) -> list[dict]:
    """把剧本行贪心合并为分镜组（对白镜）。

    规则：同 scene 内连续 lines 合并；每组 ≤ DIALOGUE_LINES_MAX 句，且未钳制
    预估时长 ≤ DIALOGUE_SECONDS_MAX 秒；scene 边界必断组。
    每组产出 {dialogue, image_prompt, video_prompt, character_names, speaker_ids}：
    - image_prompt/video_prompt 取组内第一条非空；image_prompt 缺省回退
      "场景 + 绘本风格"拼接（不含角色外形，外形由生成队列按模型能力注入）
    - character_names：组内 line.characters 并集（保序去重）
    - speaker_ids：组内说话角色 id 并集（保序去重，None 跳过）
    """
    groups: list[dict] = []
    for scene in script["scenes"]:
        setting = scene["setting"]
        current: list[dict] = []

        def flush() -> None:
            if not current:
                return
            names: list[str] = []
            speaker_ids: list[int] = []
            image_prompt = ""
            video_prompt = ""
            for line in current:
                for n in line["characters"]:
                    if n not in names:
                        names.append(n)
                cid = line["character_id"]
                if isinstance(cid, int) and cid not in speaker_ids:
                    speaker_ids.append(cid)
                if not image_prompt and line["image_prompt"]:
                    image_prompt = line["image_prompt"]
                if not video_prompt and line["video_prompt"]:
                    video_prompt = line["video_prompt"]
            if not image_prompt:
                image_prompt = (
                    f"{setting}, children picture book style, soft lighting, vertical 9:16"
                )
            groups.append(
                {
                    "dialogue": [
                        {"character_id": ln["character_id"], "en": ln["en"], "zh": ln["zh"]}
                        for ln in current
                    ],
                    "image_prompt": image_prompt,
                    "video_prompt": video_prompt,
                    "character_names": names,
                    "speaker_ids": speaker_ids,
                }
            )
            current.clear()

        for line in scene["lines"]:
            candidate = current + [line]
            if current and (
                len(candidate) > DIALOGUE_LINES_MAX
                or _raw_dialogue_seconds(candidate) > DIALOGUE_SECONDS_MAX
            ):
                flush()
            current.append(line)
        flush()
    return groups


def shots_from_script(
    project_id: int,
    script: dict,
    models: dict[str, str],
    tts_voice: str,
    resolve_character: Callable[[str], int | None],
) -> list[AvShot]:
    """把剧本拆成分镜：经 group_script_into_shots 合并，连续对答落为对白镜。

    出场角色 = 组内 character_names 经 resolve_character 解析（解析不到忽略）
    ∪ 组内说话角色 id，保序去重——说话的角色必须在画面里。
    """
    script = validate_script(script)
    shots: list[AvShot] = []
    for order, group in enumerate(group_script_into_shots(script), start=1):
        ref_ids: list[int] = []
        for name in group["character_names"]:
            cid = resolve_character(name)
            if cid is not None and cid not in ref_ids:
                ref_ids.append(cid)
        for sid in group["speaker_ids"]:
            if sid not in ref_ids:
                ref_ids.append(sid)
        shots.append(
            AvShot.create(
                project_id=project_id,
                order_index=order,
                ref_character_ids=ref_ids,
                dialogue=group["dialogue"],
                image_prompt=group["image_prompt"],
                video_prompt=group["video_prompt"],
                models=models,
                tts_voice=tts_voice,
            )
        )
    return shots


# ---------------- 聚合与合成校验 ----------------


# 说话镜走音视同出（视频自带音轨）、纯画面镜无音：audio 产物一律不参与聚合与预检
_AGGREGATE_KINDS = (AssetKind.IMAGE, AssetKind.VIDEO)


def derive_project_status(shots: list[AvShot], queue_active: bool) -> str:
    if not shots:
        return "draft"
    states = [s.asset_state(kind) for s in shots for kind in _AGGREGATE_KINDS]
    if queue_active or AssetState.RUNNING in states:
        return "generating"
    if AssetState.FAILED in states:
        return "partial_failed"
    if all(st == AssetState.SUCCESS for st in states):
        return "completed"
    return "draft"


def missing_compose_items(shots: list[AvShot]) -> list[dict]:
    """合成前置校验：video 必须全部 success（字幕随台词烧录，不依赖 image）。"""
    return [
        {"shot_id": s.id, "shot_order": s.order_index, "kind": kind.value}
        for s in shots
        for kind in (AssetKind.VIDEO,)
        if s.asset_state(kind) != AssetState.SUCCESS
    ]


def stale_items(shots: list[AvShot]) -> list[dict]:
    return [
        {"shot_id": s.id, "shot_order": s.order_index, "kind": kind.value}
        for s in shots
        for kind in AssetKind
        if s.asset_stale(kind)
    ]
