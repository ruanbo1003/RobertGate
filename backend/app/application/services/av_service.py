"""ai-videos 应用服务：角色库 + 项目工作台两组用例。

事务边界：每个用例一次 commit；需要先拿自增 id 的地方用 flush。
长耗时生成走 AvGenerationQueue（先落库 pending 再入队，保证后台任务
另开 session 能读到行）；合成走 runner.spawn 的后台协程。
"""

from __future__ import annotations

import asyncio
import logging

from collections.abc import Callable
import uuid

from app.application.dto.ai_video import (
    CharacterOut,
    CharacterRefOut,
    ComposeOut,
    GeneratedImageOut,
    ProgressOut,
    ProjectDetailOut,
    ProjectStatusOut,
    ProjectSummaryOut,
    QueueOut,
    ShotOut,
    ShotStatusOut,
    file_url,
)
from app.application.ports import (
    AudioWordAligner,
    AvGenClient,
    ComposeItem,
    TaskRunner,
    VideoComposer,
)
from app.application.services.av_queue import AvGenerationQueue, AvStorage
from app.application.services.av_subtitle import align_dialogue
from app.domain.errors import ParamException, codes, ensure_found
from app.domain.models.ai_video import (
    AssetKind,
    AssetState,
    AvCharacter,
    AvCharacterImage,
    AvProject,
    AvProjectCharacter,
    AvShot,
    CANDIDATE_IMAGES_MAX,
    derive_project_status,
    missing_compose_items,
    shots_from_script,
    stale_items,
    validate_script,
)
from app.domain.repositories.uow import UnitOfWork

logger = logging.getLogger(__name__)

# 与 infrastructure/data/av_models.py 的 default 保持一致的兜底（deps 装配时注入权威值）
_FALLBACK_MODELS = {
    "llm": "google/gemini-3.8-flash",
    "t2i": "google/gemini-3.1-flash-image",
    "i2v": "bytedance/seedance-2.0-fast",
    "tts": "openai/gpt-audio",
}
_FALLBACK_VOICE = "alloy"

_CHAR_SHEET_SUFFIX = (
    ", character sheet, standing full body, front view, "
    "children picture book style, plain soft background, vertical"
)

_SCRIPT_SYSTEM = (
    "你是一名儿童英语启蒙短剧编剧，为 3-6 岁小朋友创作角色对话小剧情。\n"
    "要求：\n"
    "1. 对白为简单英文短句（每句不超过 8 个单词），词汇适合启蒙阶段，多用重复句式。\n"
    "2. 只输出 JSON，结构固定为 "
    '{"scenes": [{"setting": "<英文场景描述>", '
    '"lines": [{"character_id": <int>, "en": "<英文台词>", "zh": "<中文释义>", '
    '"image_prompt": "<英文：该镜静态画面描述——场景/构图/光线/角色姿态>", '
    '"video_prompt": "<英文：说话角色的动作 + 运镜(static/push-in/pull-back/pan 等) + 氛围>", '
    '"characters": ["<该镜画面中出场的角色名，取自给定角色列表>"]}]}]}。\n'
    "3. character_id 必须取自给定角色列表；characters 里的名字必须与角色列表的 name 完全一致。\n"
    "4. image_prompt 只写场景与构图，不要写角色的外形细节（毛色、五官等），"
    "更不要出现 character sheet / multiple views / 多视角排版类指令；单一连贯场景。\n"
    "5. video_prompt 只描述画面动态，不要复述台词内容。\n"
    "6. 不要 markdown、不要解释、不要额外字段。"
)


class AvCharacterService:
    def __init__(self, uow: UnitOfWork, client: AvGenClient, storage: AvStorage) -> None:
        self._uow = uow
        self._client = client
        self._storage = storage

    async def _build_out(self, char: AvCharacter) -> CharacterOut:
        images = await self._uow.av_character_images.list_by_character(char.id)
        refs = await self._uow.av_project_characters.list_by_character(char.id)
        return CharacterOut.build(char, images, used_count=len(refs))

    async def list_characters(self) -> dict:
        chars = await self._uow.av_characters.list_all()
        used = await self._uow.av_project_characters.used_counts()
        out = []
        for c in chars:
            images = await self._uow.av_character_images.list_by_character(c.id)
            out.append(CharacterOut.build(c, images, used_count=used.get(c.id, 0)))
        return {"characters": out}

    async def create_character(
        self,
        name: str,
        appearance_prompt: str,
        personality: str | None,
        voice_desc: str | None = None,
    ) -> dict:
        char = AvCharacter.create(name, appearance_prompt, personality, voice_desc)
        if await self._uow.av_characters.find_by_name(char.name) is not None:
            raise ParamException(codes.AV_PARAM_INVALID, "角色名称已存在")
        self._uow.av_characters.add(char)
        await self._uow.flush()
        await self._uow.commit()
        return {"character": CharacterOut.build(char, [], used_count=0)}

    async def update_character(
        self,
        character_id: int,
        name: str | None,
        appearance_prompt: str | None,
        personality: str | None,
        cover_image_id: int | None,
        voice_desc: str | None = None,
    ) -> dict:
        char = ensure_found(
            await self._uow.av_characters.find_by_id(character_id),
            codes.AV_NOT_FOUND,
            "角色不存在",
        )
        if name is not None and name.strip() != char.name:
            if await self._uow.av_characters.find_by_name(name.strip()) is not None:
                raise ParamException(codes.AV_PARAM_INVALID, "角色名称已存在")
        char.apply_update(name, appearance_prompt, personality, voice_desc)
        if cover_image_id is not None:
            image = await self._uow.av_character_images.find_by_id(cover_image_id)
            if image is None or image.character_id != char.id:
                raise ParamException(codes.AV_PARAM_INVALID, "cover_image_id 不在候选集内")
            char.cover_image_id = cover_image_id
        await self._uow.commit()
        return {"character": await self._build_out(char)}

    async def delete_character(self, character_id: int) -> None:
        char = ensure_found(
            await self._uow.av_characters.find_by_id(character_id),
            codes.AV_NOT_FOUND,
            "角色不存在",
        )
        refs = await self._uow.av_project_characters.list_by_character(character_id)
        if refs:
            used_by = []
            for ref in refs:
                project = await self._uow.av_projects.find_by_id(ref.project_id)
                used_by.append(
                    {"project_id": ref.project_id, "title": project.title if project else ""}
                )
            raise ParamException(
                codes.AV_CHARACTER_IN_USE,
                f"角色已被 {len(refs)} 个视频引用，不能删除",
                data={"used_by": used_by},
            )
        self._storage.delete_tree(f"characters/{character_id}")
        await self._uow.av_characters.delete(char)
        await self._uow.commit()

    async def generate_image(
        self, character_id: int, model: str, prompt: str | None
    ) -> GeneratedImageOut:
        char = ensure_found(
            await self._uow.av_characters.find_by_id(character_id),
            codes.AV_NOT_FOUND,
            "角色不存在",
        )
        effective = (prompt or "").strip() or (char.appearance_prompt + _CHAR_SHEET_SUFFIX)
        data = await self._client.generate_image(effective, model, None)
        rel = self._storage.save(
            f"characters/{character_id}/{uuid.uuid4().hex[:12]}.png", data
        )
        image = AvCharacterImage.create(character_id=character_id, path=rel)
        self._uow.av_character_images.add(image)
        await self._uow.flush()

        existing = await self._uow.av_character_images.list_by_character(character_id)
        candidates = [i for i in existing if i.id != image.id] + [image]
        if len(candidates) > CANDIDATE_IMAGES_MAX:
            victim = next(
                (i for i in candidates if i.id != char.cover_image_id and i.id != image.id),
                None,
            )
            if victim is not None:
                await self._uow.av_character_images.delete(victim)
                self._storage.delete(victim.path)
        if char.cover_image_id is None:
            char.cover_image_id = image.id
        char.touch()
        await self._uow.commit()
        return GeneratedImageOut(id=image.id, url=file_url(rel) or "")


class AvProjectService:
    def __init__(
        self,
        uow: UnitOfWork,
        client: AvGenClient,
        queue: AvGenerationQueue,
        storage: AvStorage,
        composer: VideoComposer,
        runner: TaskRunner,
        uow_factory,
        model_defaults: dict[str, str] | None = None,
        voice_default: str = _FALLBACK_VOICE,
        whisper: AudioWordAligner | None = None,
        model_known: Callable[[str, str], bool] | None = None,
        image_reference_mode: Callable[[str], str] | None = None,
    ) -> None:
        self._uow = uow
        self._client = client
        self._queue = queue
        self._storage = storage
        self._composer = composer
        self._runner = runner
        self._uow_factory = uow_factory
        self._model_defaults = model_defaults or dict(_FALLBACK_MODELS)
        self._voice_default = voice_default
        self._whisper = whisper
        # 注册表判据（deps 注入 is_known_model）；None = 不校验（兼容旧装配/测试）
        self._model_known = model_known
        # t2i 参考图能力档判据（deps 注入 reference_mode）；None = 不校验
        self._image_reference_mode = image_reference_mode

    # ---------------- 内部取数 ----------------

    async def _get_project(self, project_id: int) -> AvProject:
        return ensure_found(
            await self._uow.av_projects.find_by_id(project_id),
            codes.AV_NOT_FOUND,
            "项目不存在",
        )

    async def _get_shot(self, project_id: int, shot_id: int) -> AvShot:
        shot = await self._uow.av_shots.find_by_id(shot_id)
        if shot is None or shot.project_id != project_id:
            raise ParamException(codes.AV_NOT_FOUND, "分镜不存在")
        return shot

    def _queue_active(self, project_id: int) -> bool:
        pending, running = self._queue.counts(project_id)
        return pending + running > 0

    async def _character_refs(self, project_id: int) -> list[CharacterRefOut]:
        refs = await self._uow.av_project_characters.list_by_project(project_id)
        out: list[CharacterRefOut] = []
        for ref in refs:
            char = await self._uow.av_characters.find_by_id(ref.character_id)
            if char is None:
                continue
            cover = None
            if char.cover_image_id:
                cover = await self._uow.av_character_images.find_by_id(char.cover_image_id)
            out.append(
                CharacterRefOut(
                    id=char.id,
                    name=char.name,
                    cover_image_url=file_url(cover.path) if cover else None,
                )
            )
        return out

    async def _detail(self, project: AvProject) -> ProjectDetailOut:
        shots = await self._uow.av_shots.list_by_project(project.id)
        return ProjectDetailOut(
            id=project.id,
            title=project.title,
            synopsis=project.synopsis,
            status=derive_project_status(shots, self._queue_active(project.id)),
            target_duration=project.target_duration,
            characters=await self._character_refs(project.id),
            default_models=dict(project.default_models),
            tts_voice=project.tts_voice,
            script=project.script,
            compose=ComposeOut.build(project),
            shots=[ShotOut.build(s) for s in shots],
        )

    # ---------------- 项目 CRUD ----------------

    async def list_projects(self, page: int, page_size: int) -> dict:
        projects, total = await self._uow.av_projects.list_page(page, page_size)
        items = []
        for p in projects:
            shots = await self._uow.av_shots.list_by_project(p.id)
            items.append(ProjectSummaryOut.build(p, shots, self._queue_active(p.id)))
        return {"total": total, "items": items}

    async def create_project(
        self,
        title: str,
        synopsis: str,
        character_ids: list[int],
        target_duration: int,
        default_models: dict[str, str] | None,
        tts_voice: str | None,
    ) -> dict:
        if not character_ids or len(character_ids) > 4:
            raise ParamException(codes.AV_PARAM_INVALID, "出场角色须为 1-4 个")
        for cid in character_ids:
            if await self._uow.av_characters.find_by_id(cid) is None:
                raise ParamException(codes.AV_PARAM_INVALID, f"角色不存在：{cid}")
        models = {**self._model_defaults, **(default_models or {})}
        project = AvProject.create(
            title=title,
            synopsis=synopsis,
            target_duration=target_duration,
            default_models=models,
            tts_voice=tts_voice or self._voice_default,
        )
        self._uow.av_projects.add(project)
        await self._uow.flush()
        for cid in character_ids:
            self._uow.av_project_characters.add(
                AvProjectCharacter(project_id=project.id, character_id=cid)
            )
        await self._uow.commit()
        return {"project": await self._detail(project)}

    async def get_project(self, project_id: int) -> dict:
        project = await self._get_project(project_id)
        return {"project": await self._detail(project)}

    async def update_project(
        self,
        project_id: int,
        title: str | None,
        synopsis: str | None,
        default_models: dict[str, str] | None,
        tts_voice: str | None,
    ) -> dict:
        project = await self._get_project(project_id)
        if title is not None:
            project.title = title.strip() or project.title
        if synopsis is not None:
            project.synopsis = synopsis.strip() or project.synopsis
        if default_models:
            project.default_models = {**project.default_models, **default_models}
        if tts_voice:
            project.tts_voice = tts_voice
        project.touch()
        await self._uow.commit()
        return {"project": await self._detail(project)}

    async def delete_project(self, project_id: int) -> None:
        project = await self._get_project(project_id)
        self._queue.cancel_project(project_id)
        self._storage.delete_tree(f"projects/{project_id}")
        await self._uow.av_projects.delete(project)
        await self._uow.commit()

    # ---------------- 剧本 / 分镜 ----------------

    async def generate_script(self, project_id: int, model: str | None) -> dict:
        project = await self._get_project(project_id)
        chars = await self._character_refs(project_id)
        char_lines = []
        for ref in chars:
            char = await self._uow.av_characters.find_by_id(ref.id)
            if char is None:
                continue
            char_lines.append(
                f"- character_id={char.id} name={char.name} "
                f"personality={char.personality or 'n/a'} appearance={char.appearance_prompt}"
            )
        target_lines = max(4, round(project.target_duration / 5))
        user = (
            f"角色列表：\n{chr(10).join(char_lines)}\n\n"
            f"故事梗概：{project.synopsis}\n"
            f"目标视频时长：{project.target_duration} 秒，"
            f"请生成约 {target_lines} 句对白（每句一镜，单镜约 5 秒）。"
        )
        raw = await self._client.generate_json(
            _SCRIPT_SYSTEM,
            user,
            self._resolve_model("llm", model or project.default_models["llm"]),
        )
        script = validate_script(raw)
        project.set_script(script)
        await self._uow.commit()
        return script

    async def update_script(self, project_id: int, script: dict) -> dict:
        project = await self._get_project(project_id)
        project.set_script(script)
        shots = await self._uow.av_shots.list_by_project(project_id)
        await self._uow.commit()
        return {"shots_exist": len(shots) > 0}

    async def split_shots(
        self, project_id: int, model: str | None, confirm_replace: bool
    ) -> list[ShotOut]:
        project = await self._get_project(project_id)
        if not project.script:
            raise ParamException(codes.AV_PRECONDITION_FAILED, "请先生成剧本")
        existing = await self._uow.av_shots.list_by_project(project_id)
        if existing and not confirm_replace:
            raise ParamException(
                codes.AV_SHOTS_CONFIRM_REQUIRED,
                "已存在分镜，重拆将删除全部产物",
                data={"existing_shot_count": len(existing)},
            )
        self._queue.cancel_project(project_id)
        await self._uow.av_shots.delete_by_project(project_id)

        refs = await self._character_refs(project_id)
        name_to_id = {r.name.strip().lower(): r.id for r in refs}
        shots = shots_from_script(
            project_id=project_id,
            script=project.script,
            models=dict(project.default_models),
            tts_voice=project.tts_voice,
            resolve_character=lambda name: name_to_id.get(name.strip().lower()),
        )
        for shot in shots:
            self._uow.av_shots.add(shot)
        project.compose_state = "none"
        project.compose_path = None
        project.compose_error = None
        project.compose_stale = False
        project.touch()
        await self._uow.flush()
        await self._uow.commit()
        return [ShotOut.build(s) for s in shots]

    async def create_shot(self, project_id: int, after_shot_id: int | None) -> dict:
        project = await self._get_project(project_id)
        shots = await self._uow.av_shots.list_by_project(project_id)
        insert_at = 0
        if after_shot_id is not None:
            idx = next((i for i, s in enumerate(shots) if s.id == after_shot_id), None)
            if idx is None:
                raise ParamException(codes.AV_NOT_FOUND, "after_shot_id 分镜不存在")
            insert_at = idx + 1
        shot = AvShot.create(
            project_id=project_id,
            order_index=insert_at + 1,
            ref_character_ids=[],
            dialogue=[],
            image_prompt="",
            models=dict(project.default_models),
            tts_voice=project.tts_voice,
        )
        self._uow.av_shots.add(shot)
        for i, s in enumerate(shots[insert_at:], start=insert_at + 1):
            s.order_index = i + 1
        project.touch()
        await self._uow.flush()
        await self._uow.commit()
        return {"shot": ShotOut.build(shot)}

    async def update_shot(self, project_id: int, shot_id: int, patch: dict) -> dict:
        project = await self._get_project(project_id)
        shot = await self._get_shot(project_id, shot_id)
        if "ref_character_ids" in patch:
            refs = await self._uow.av_project_characters.list_by_project(project_id)
            allowed = {r.character_id for r in refs}
            illegal = [cid for cid in patch["ref_character_ids"] if cid not in allowed]
            if illegal:
                raise ParamException(
                    codes.AV_PARAM_INVALID, f"出场角色不属于本项目：{illegal}"
                )
        staled = shot.apply_patch(**patch)
        if staled:
            project.mark_compose_stale()
        project.touch()
        await self._uow.commit()
        return {"shot": ShotOut.build(shot)}

    async def delete_shot(self, project_id: int, shot_id: int) -> None:
        project = await self._get_project(project_id)
        shot = await self._get_shot(project_id, shot_id)
        await self._uow.av_shots.delete(shot)
        shots = await self._uow.av_shots.list_by_project(project_id)
        for i, s in enumerate(sorted((x for x in shots if x.id != shot_id), key=lambda x: x.order_index)):
            s.order_index = i + 1
        project.mark_compose_stale()
        project.touch()
        await self._uow.commit()

    async def reorder_shots(self, project_id: int, shot_ids: list[int]) -> None:
        project = await self._get_project(project_id)
        shots = await self._uow.av_shots.list_by_project(project_id)
        if sorted(shot_ids) != sorted(s.id for s in shots):
            raise ParamException(
                codes.AV_PARAM_INVALID, "shot_ids 必须恰好覆盖全部分镜"
            )
        by_id = {s.id: s for s in shots}
        for i, sid in enumerate(shot_ids):
            by_id[sid].order_index = i + 1
        project.mark_compose_stale()
        project.touch()
        await self._uow.commit()

    # ---------------- 生成 / 合成 ----------------

    _KIND_MODEL_KEY = {
        AssetKind.IMAGE: "t2i",
        AssetKind.VIDEO: "i2v",
        AssetKind.AUDIO: "tts",
    }

    def _resolve_model(self, kind_key: str, candidate: str) -> str:
        """活配置回退：老项目落库的失效模型 id（如 OpenRouter 闭源系）
        读取时回退到该能力线当前默认，不改库（kie 迁移决策 1）。"""
        if self._model_known is not None and not self._model_known(kind_key, candidate):
            fallback = self._model_defaults.get(kind_key, candidate)
            logger.info("av 模型已失效，读取回退：%s %s -> %s", kind_key, candidate, fallback)
            candidate = fallback
        # 分镜图只能用带参考图（multi）的模型：none 档会丢角色一致性
        # （Robert 2026-11-14 拍板；角色设定图不走此路径不受限）
        if (
            kind_key == "t2i"
            and self._image_reference_mode is not None
            and self._image_reference_mode(candidate) != "multi"
        ):
            fallback = self._model_defaults.get("t2i", candidate)
            logger.info("分镜图模型无参考图能力，回退：%s -> %s", candidate, fallback)
            candidate = fallback
        return candidate

    async def generate_asset(
        self,
        project_id: int,
        shot_id: int,
        kind: AssetKind,
        model: str | None,
        voice: str | None,
    ) -> None:
        project = await self._get_project(project_id)
        shot = await self._get_shot(project_id, shot_id)
        if self._queue.is_active(shot_id, kind):
            raise ParamException(codes.AV_ASSET_BUSY, "该产物正在生成中")
        if kind == AssetKind.VIDEO and shot.asset_state(AssetKind.IMAGE) != AssetState.SUCCESS:
            raise ParamException(codes.AV_PRECONDITION_FAILED, "请先生成分镜图")
        if kind == AssetKind.AUDIO and shot.has_dialogue:
            raise ParamException(codes.AV_PARAM_INVALID, "对白镜无独立配音")
        if kind == AssetKind.AUDIO and not shot.line_en.strip():
            raise ParamException(codes.AV_PRECONDITION_FAILED, "请先填写台词")
        kind_key = self._KIND_MODEL_KEY[kind]
        effective_model = self._resolve_model(
            kind_key, model or project.default_models[kind_key]
        )
        effective_voice = voice or project.tts_voice if kind == AssetKind.AUDIO else None
        shot.mark_pending(kind, effective_model, effective_voice)
        project.touch()
        await self._uow.commit()
        self._queue.enqueue(project_id, shot_id, kind, effective_model, effective_voice)

    async def generate_all(
        self, project_id: int, types: list[AssetKind], scope: str
    ) -> dict[str, int]:
        project = await self._get_project(project_id)
        shots = await self._uow.av_shots.list_by_project(project_id)
        planned: list[tuple[AvShot, AssetKind, str, str | None]] = []
        for shot in shots:
            for kind in types:
                if self._queue.is_active(shot.id, kind):
                    continue
                state = shot.asset_state(kind)
                if state == AssetState.RUNNING:
                    continue
                needs = (
                    scope == "all"
                    or state in (AssetState.PENDING, AssetState.FAILED)
                    or shot.asset_stale(kind)
                )
                if not needs:
                    continue
                if kind == AssetKind.AUDIO and (shot.has_dialogue or not shot.line_en.strip()):
                    continue
                kind_key = self._KIND_MODEL_KEY[kind]
                model = self._resolve_model(kind_key, project.default_models[kind_key])
                voice = project.tts_voice if kind == AssetKind.AUDIO else None
                shot.mark_pending(kind, model, voice)
                planned.append((shot, kind, model, voice))
        project.touch()
        await self._uow.commit()
        enqueued = {k.value: 0 for k in AssetKind}
        for shot, kind, model, voice in planned:
            if self._queue.enqueue(project_id, shot.id, kind, model, voice):
                enqueued[kind.value] += 1
        return enqueued

    def cancel_queue(self, project_id: int) -> int:
        return self._queue.cancel_project(project_id)

    async def compose(self, project_id: int, ignore_stale: bool) -> None:
        project = await self._get_project(project_id)
        shots = await self._uow.av_shots.list_by_project(project_id)
        if not shots:
            raise ParamException(codes.AV_PRECONDITION_FAILED, "还没有分镜")
        missing = missing_compose_items(shots)
        if missing:
            raise ParamException(
                codes.AV_PRECONDITION_FAILED,
                f"还有 {len(missing)} 项产物未就绪",
                data={"missing": missing},
            )
        stale = stale_items(shots)
        if stale and not ignore_stale:
            raise ParamException(
                codes.AV_STALE_CONFIRM_REQUIRED,
                f"存在 {len(stale)} 项过期产物",
                data={"stale_items": stale},
            )
        ordered = sorted(shots, key=lambda x: x.order_index)
        project.mark_compose_running()
        await self._uow.commit()
        self._runner.spawn(self._run_compose(project_id, ordered))

    async def _build_compose_items(self, shots: list[AvShot]) -> list[ComposeItem]:
        """组装合成输入：镜有独立音频文件 → mux；否则（对白镜）用视频自带音轨 +
        whisper 词级对齐字幕。whisper 调用耗时，必须在后台协程里做（不占请求事务）。
        """
        items: list[ComposeItem] = []
        for s in shots:
            video = self._storage.absolute(s.video_path or "")
            audio = self._storage.absolute(s.audio_path) if s.audio_path else None
            video_dur = await self._composer.probe_duration(video) or s.duration_estimate
            if audio is not None:
                audio_dur = await self._composer.probe_duration(audio) or video_dur
                duration = max(video_dur, audio_dur)
            else:
                duration = video_dur
            if s.has_dialogue and audio is None:
                # 对齐 key 必须是纯英文（whisper 只能匹配口语文本）；显示文本
                # 可以是 en\nzh 双行——两者分开，对齐完再把时间戳贴回显示文本，
                # 否则中文字符被当 token 计入总数，匹配率结构性地必然 <50%。
                spoken = [ln["en"] for ln in s.dialogue]
                display = [
                    (f"{ln['en']}\n{ln['zh']}" if ln["zh"] else ln["en"])
                    for ln in s.dialogue
                ]
                try:
                    words = (
                        await asyncio.to_thread(self._whisper.transcribe_words, video)
                        if self._whisper
                        else []
                    )
                except Exception:  # noqa: BLE001
                    logger.warning("whisper 转写失败，回退按台词长度均分镜时长", exc_info=True)
                    words = []
                aligned = align_dialogue(spoken, words, duration)
                subtitles = [
                    (text, start, end) for text, (_, start, end) in zip(display, aligned)
                ]
            else:
                text = s.line_en or (s.dialogue[0]["en"] if s.dialogue else "")
                subtitles = [(text, 0.0, duration)]
            items.append(ComposeItem(video=video, audio=audio, subtitles=subtitles))
        return items

    async def _run_compose(self, project_id: int, shots: list[AvShot]) -> None:
        rel_out = f"projects/{project_id}/final.mp4"
        error: str | None = None
        try:
            items = await self._build_compose_items(shots)
            await self._composer.compose(items, self._storage.absolute(rel_out))
        except Exception as e:  # noqa: BLE001
            logger.exception("compose failed for project=%s", project_id)
            error = str(e)[:500]
        async with self._uow_factory() as uow:
            project = await uow.av_projects.find_by_id(project_id)
            if project is None:
                return
            if error is None:
                project.mark_compose_succeeded(rel_out)
            else:
                project.mark_compose_failed(error)
            await uow.commit()

    # ---------------- 轮询 / 下载 ----------------

    async def get_status(self, project_id: int) -> ProjectStatusOut:
        project = await self._get_project(project_id)
        shots = await self._uow.av_shots.list_by_project(project_id)
        pending, running = self._queue.counts(project_id)
        progress = {
            kind.value: ProgressOut(
                done=sum(1 for s in shots if s.asset_state(kind) == AssetState.SUCCESS),
                total=len(shots),
            )
            for kind in AssetKind
        }
        return ProjectStatusOut(
            status=derive_project_status(shots, pending + running > 0),
            queue=QueueOut(
                pending=pending,
                running=running,
                paused=self._queue.paused,
                paused_reason=self._queue.paused_reason,
            ),
            progress=progress,
            stale_count=len(stale_items(shots)),
            compose=ComposeOut.build(project),
            shots=[ShotStatusOut.build(s) for s in shots],
        )

    async def download_path(self, project_id: int):
        project = await self._get_project(project_id)
        if project.compose_state != "success" or not project.compose_path:
            raise ParamException(codes.AV_PRECONDITION_FAILED, "成片尚未合成")
        return self._storage.absolute(project.compose_path), f"{project.title}.mp4"
