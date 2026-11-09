"""ai-videos 进程内生成队列。

规则（docs/api/ai-videos.md 第五节）：
- 并发上限：image 2 / video 1 / audio 2，同类排队 FIFO（semaphore 排队序）
- video 任务派发前等待同镜 image 成功；image 失败则 video 直接置失败
- 同一产物已有排队/进行中任务 → enqueue 返回 False（上层转 2006）
- AV_UPSTREAM_QUOTA（余额/Key 全局错误）→ 暂停整个队列、产物回退 pending；
  新的 enqueue 视为用户已处理，自动解除暂停
- 失败不自动重试，由用户手动重发

队列脱离请求生命周期，经 uow_factory 自开工作单元写回状态。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Protocol

from app.application.ports import AvGenClient, TaskRunner
from app.application.services.av_dialogue import build_dialogue_prompt
from app.domain.errors import ServerException, codes
from app.domain.models.ai_video import AssetKind, AssetState

logger = logging.getLogger(__name__)

_LIMITS: dict[AssetKind, int] = {
    AssetKind.IMAGE: 2,
    AssetKind.VIDEO: 1,
    AssetKind.AUDIO: 2,
}
_EXT: dict[AssetKind, str] = {
    AssetKind.IMAGE: "png",
    AssetKind.VIDEO: "mp4",
    AssetKind.AUDIO: "mp3",
}
_WAIT_IMAGE_TIMEOUT = 900.0  # video 等待前置分镜图的上限（秒）


class AvStorage(Protocol):
    """产物文件存取（实现见 infrastructure/av_storage.py）。"""

    def save(self, rel_path: str, data: bytes) -> str: ...

    def read(self, rel_path: str) -> bytes: ...

    async def probe_duration(self, rel_path: str) -> float | None: ...

    def delete(self, rel_path: str) -> None: ...


@dataclass
class _Item:
    project_id: int
    shot_id: int
    kind: AssetKind
    model: str
    voice: str | None = None
    state: str = field(default="queued")  # queued | running
    cancelled: bool = False


class AvGenerationQueue:
    def __init__(
        self,
        uow_factory,
        client: AvGenClient,
        storage: AvStorage,
        runner: TaskRunner,
        reference_mode: Callable[[str], str],
        poll_interval: float = 1.0,
    ) -> None:
        self._uow_factory = uow_factory
        self._client = client
        self._storage = storage
        self._runner = runner
        self._reference_mode = reference_mode
        self._poll = poll_interval
        self._sems = {kind: asyncio.Semaphore(limit) for kind, limit in _LIMITS.items()}
        self._items: dict[tuple[int, AssetKind], _Item] = {}
        self._paused = False
        self._paused_reason: str | None = None

    # ---------------- 对外状态 ----------------

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def paused_reason(self) -> str | None:
        return self._paused_reason

    @property
    def active_count(self) -> int:
        return len(self._items)

    def is_active(self, shot_id: int, kind: AssetKind) -> bool:
        return (shot_id, kind) in self._items

    def counts(self, project_id: int) -> tuple[int, int]:
        """(排队中, 进行中)。"""
        pending = running = 0
        for item in self._items.values():
            if item.project_id != project_id or item.cancelled:
                continue
            if item.state == "running":
                running += 1
            else:
                pending += 1
        return pending, running

    # ---------------- 入队 / 取消 ----------------

    def enqueue(
        self,
        project_id: int,
        shot_id: int,
        kind: AssetKind,
        model: str,
        voice: str | None = None,
    ) -> bool:
        key = (shot_id, kind)
        if key in self._items:
            return False
        # 用户重新发起生成 = 已处理全局错误（换 Key/充值），自动恢复队列
        self._paused = False
        self._paused_reason = None
        item = _Item(project_id=project_id, shot_id=shot_id, kind=kind, model=model, voice=voice)
        self._items[key] = item
        self._runner.spawn(self._run(item))
        return True

    def cancel_project(self, project_id: int) -> int:
        """取消该项目所有排队中任务（进行中的跑完为止），返回取消数量。"""
        cancelled = 0
        for key, item in list(self._items.items()):
            if item.project_id == project_id and item.state == "queued":
                item.cancelled = True
                self._items.pop(key, None)
                cancelled += 1
        return cancelled

    # ---------------- 执行 ----------------

    async def _run(self, item: _Item) -> None:
        key = (item.shot_id, item.kind)
        try:
            if item.kind == AssetKind.VIDEO:
                if not await self._wait_for_image(item):
                    return
            while self._paused and not item.cancelled:
                await asyncio.sleep(self._poll)
            if item.cancelled:
                return
            async with self._sems[item.kind]:
                if item.cancelled:
                    return
                item.state = "running"
                await self._mark(item, AssetState.RUNNING)
                try:
                    data, model_tag = await self._generate(item)
                except ServerException as e:
                    if e.code == codes.AV_UPSTREAM_QUOTA:
                        self._paused = True
                        self._paused_reason = e.message
                        await self._mark(item, AssetState.PENDING)
                    else:
                        await self._fail(item, e.message)
                    return
                except Exception as e:  # noqa: BLE001
                    logger.exception("av 生成异常 shot=%s kind=%s", item.shot_id, item.kind)
                    await self._fail(item, str(e)[:300])
                    return
                await self._succeed(item, data, model_tag)
        finally:
            self._items.pop(key, None)

    async def _wait_for_image(self, item: _Item) -> bool:
        """video 前置：等同镜 image 成功。返回 False 表示任务已终结（失败/取消）。"""
        waited = 0.0
        while waited < _WAIT_IMAGE_TIMEOUT:
            if item.cancelled:
                return False
            async with self._uow_factory() as uow:
                shot = await uow.av_shots.find_by_id(item.shot_id)
                if shot is None:
                    return False
                state = shot.asset_state(AssetKind.IMAGE)
            if state == AssetState.SUCCESS:
                return True
            if state == AssetState.FAILED:
                await self._fail(item, "前置分镜图失败")
                return False
            await asyncio.sleep(self._poll)
            waited += self._poll
        await self._fail(item, "等待分镜图超时")
        return False

    async def _build_image_request(
        self, uow, shot, model: str
    ) -> tuple[str, list[bytes]]:
        """按模型参考能力拼装分镜图请求。

        multi：有封面的出场角色按序进参考图并点名，无封面的拼外形描述；
        none：全部角色拼外形描述。点名/兜底文本只在此动态生成，不落库。
        """
        mode = self._reference_mode(model)
        refs: list[bytes] = []
        prefix_parts: list[str] = []
        for cid in list(shot.ref_character_ids or []):
            char = await uow.av_characters.find_by_id(cid)
            if char is None:
                continue
            cover_bytes: bytes | None = None
            if mode == "multi" and char.cover_image_id:
                cover = await uow.av_character_images.find_by_id(char.cover_image_id)
                if cover is not None:
                    cover_bytes = self._storage.read(cover.path)
            if cover_bytes is not None:
                refs.append(cover_bytes)
                prefix_parts.append(
                    f"{char.name} is the character in reference image {len(refs)}."
                )
            else:
                prefix_parts.append(f"{char.name}: {char.appearance_prompt}.")
        if refs:
            # 参考图多为多视角设定图：只取外形，严禁复刻 sheet 版式
            prefix_parts.append(
                "Use the reference images only for the characters' appearance; "
                "do not copy the character-sheet layout; "
                "render one single coherent scene."
            )
        prompt = shot.image_prompt
        if prefix_parts:
            prompt = " ".join(prefix_parts) + " " + prompt
        return prompt, refs

    async def _collect_speakers(self, uow, dialogue: list[dict]) -> list[dict]:
        """dialogue 里出现过的说话角色（按首次出现保序去重），缺字符档忽略。"""
        speakers: list[dict] = []
        seen: set[int] = set()
        for line in dialogue:
            cid = line["character_id"]
            if cid is None or cid in seen:
                continue
            seen.add(cid)
            char = await uow.av_characters.find_by_id(cid)
            if char is not None:
                speakers.append({"id": cid, "name": char.name, "voice_desc": char.voice_desc})
        return speakers

    async def _generate(self, item: _Item) -> tuple[bytes, str | None]:
        # 先在 uow 内读齐纯数据再关闭会话：上游生成可长达 10 分钟，
        # 期间不得占用数据库连接/事务。
        async with self._uow_factory() as uow:
            shot = await uow.av_shots.find_by_id(item.shot_id)
            if shot is None:
                raise ServerException(codes.AV_UPSTREAM_FAILED, "分镜已删除")
            if item.kind == AssetKind.IMAGE:
                prompt, refs = await self._build_image_request(uow, shot, item.model)
            elif item.kind == AssetKind.VIDEO:
                image_bytes = self._storage.read(shot.image_path or "")
                duration = round(shot.duration_estimate)
                is_dialogue = shot.has_dialogue
                if is_dialogue:
                    speakers = await self._collect_speakers(uow, shot.dialogue)
                    dialogue_prompt = build_dialogue_prompt(
                        shot.image_prompt, speakers, shot.dialogue
                    )
                else:
                    video_prompt = shot.video_prompt or shot.image_prompt
            else:
                line_en = shot.line_en
                voice = item.voice or shot.audio_voice

        if item.kind == AssetKind.IMAGE:
            data = await self._client.generate_image(prompt, item.model, refs or None)
            return data, None
        if item.kind == AssetKind.VIDEO:
            if is_dialogue:
                return await self._client.generate_dialogue_video(
                    image_bytes, dialogue_prompt, duration_seconds=duration
                )
            data = await self._client.generate_video(
                image_bytes, video_prompt, item.model, duration_seconds=duration
            )
            return data, None
        data = await self._client.generate_speech(line_en, item.model, voice)
        return data, None

    async def _succeed(
        self, item: _Item, data: bytes, model_tag: str | None = None
    ) -> None:
        rel_path = self._storage.save(
            f"projects/{item.project_id}/shots/{item.shot_id}/{item.kind.value}.{_EXT[item.kind]}",
            data,
        )
        duration: float | None = None
        if item.kind == AssetKind.AUDIO:
            duration = await self._storage.probe_duration(rel_path)
        async with self._uow_factory() as uow:
            shot = await uow.av_shots.find_by_id(item.shot_id)
            if shot is None:
                return
            shot.mark_succeeded(item.kind, rel_path, audio_duration=duration)
            if model_tag:
                # 对白镜：路由实际落地的渠道:模型（kie:... / openrouter:...），覆盖入队时的占位模型
                shot.video_model = model_tag
                if shot.audio_path:
                    # 旧迁移镜残留的 TTS 配音已失效：视频现在自带同步语音，
                    # 不清空的话合成会继续 mux 旧音频、丢弃新视频的口型同步声音
                    self._storage.delete(shot.audio_path)
                    shot.retire_audio()
            if item.voice:
                shot.audio_voice = item.voice
            project = await uow.av_projects.find_by_id(item.project_id)
            if project is not None:
                project.mark_compose_stale()
                project.touch()
            await uow.commit()

    async def _mark(self, item: _Item, state: AssetState) -> None:
        async with self._uow_factory() as uow:
            shot = await uow.av_shots.find_by_id(item.shot_id)
            if shot is None:
                return
            if state == AssetState.RUNNING:
                shot.mark_running(item.kind)
            else:
                setattr(shot, f"{item.kind.value}_state", state)
            await uow.commit()

    async def _fail(self, item: _Item, error: str) -> None:
        async with self._uow_factory() as uow:
            shot = await uow.av_shots.find_by_id(item.shot_id)
            if shot is None:
                return
            shot.mark_failed(item.kind, error)
            await uow.commit()
