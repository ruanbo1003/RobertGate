"""AvGenerationQueue 单元测试：并发上限、video 等图、失败传导、取消、配额暂停。

用内存版 uow_factory + 假客户端/存储驱动真实队列逻辑，runner 用真 asyncio。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import pytest

from app.application.services.av_queue import AvGenerationQueue
from app.domain.errors import ServerException, codes
from app.domain.models.ai_video import (
    AssetKind,
    AssetState,
    AvCharacter,
    AvCharacterImage,
    AvProject,
    AvShot,
    ComposeState,
)
from app.infrastructure.tasks import AsyncioTaskRunner

DEFAULT_MODELS = {
    "llm": "llm-m",
    "t2i": "t2i-m",
    "i2v": "i2v-m",
    "tts": "tts-m",
}


class MemRepo:
    def __init__(self, rows: dict):
        self.rows = rows

    async def find_by_id(self, id_):
        return self.rows.get(id_)


class MemUow:
    def __init__(self, store):
        self.av_shots = MemRepo(store["shots"])
        self.av_projects = MemRepo(store["projects"])
        self.av_characters = MemRepo(store["characters"])
        self.av_character_images = MemRepo(store["character_images"])
        self.commits = 0

    async def commit(self):
        self.commits += 1


def make_store():
    project = AvProject.create(
        title="EP", synopsis="s", target_duration=60,
        default_models=DEFAULT_MODELS, tts_voice="alex",
    )
    project.id = 1
    shots = {}
    for i in range(1, 7):
        s = AvShot.create(
            project_id=1, order_index=i,
            speaker_character_id=10, ref_character_ids=[10],
            line_en=f"Line {i}!", line_zh="", image_prompt=f"prompt {i}",
            models=DEFAULT_MODELS, tts_voice="alex",
        )
        s.id = i
        shots[i] = s
    char = AvCharacter.create(name="Momo", appearance_prompt="a cute fox", personality=None)
    char.id = 10
    char.cover_image_id = 100
    cover = AvCharacterImage.create(character_id=10, path="characters/10/100.png")
    cover.id = 100
    char2 = AvCharacter.create(name="Kuku", appearance_prompt="a small bear", personality=None)
    char2.id = 12
    char2.cover_image_id = 120
    cover2 = AvCharacterImage.create(character_id=12, path="characters/12/120.png")
    cover2.id = 120
    char3 = AvCharacter.create(name="Lulu", appearance_prompt="a grey bunny", personality=None)
    char3.id = 11  # 无封面
    return {
        "projects": {1: project},
        "shots": shots,
        "characters": {10: char, 11: char3, 12: char2},
        "character_images": {100: cover, 120: cover2},
    }


class FakeClient:
    def __init__(self):
        self.calls: list[tuple] = []
        self.concurrent = 0
        self.max_concurrent = 0
        self.delay = 0.02
        self.fail_kinds: dict[str, Exception] = {}
        self.gate: asyncio.Event | None = None

    async def _work(self, kind: str, *args):
        self.calls.append((kind, *args))
        if kind in self.fail_kinds:
            raise self.fail_kinds[kind]
        self.concurrent += 1
        self.max_concurrent = max(self.max_concurrent, self.concurrent)
        try:
            if self.gate is not None:
                await self.gate.wait()
            else:
                await asyncio.sleep(self.delay)
        finally:
            self.concurrent -= 1
        return b"bytes-" + kind.encode()

    async def generate_image(self, prompt, model, reference_images=None):
        return await self._work("image", prompt, model, reference_images)

    async def generate_video(self, image, prompt, model, duration_seconds=5):
        return await self._work("video", prompt, model, duration_seconds)

    async def generate_speech(self, text, model, voice):
        return await self._work("audio", text, model, voice)

    async def generate_json(self, system, user, model):
        return {}


class FakeStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}
        self.files: dict[str, bytes] = {
            "characters/10/100.png": b"cover-bytes",
            "characters/12/120.png": b"cover2-bytes",
        }

    def save(self, rel_path: str, data: bytes) -> str:
        self.saved[rel_path] = data
        return rel_path

    def read(self, rel_path: str) -> bytes:
        if rel_path in self.saved:
            return self.saved[rel_path]
        return self.files[rel_path]

    async def probe_duration(self, rel_path: str) -> float | None:
        return 3.3


@pytest.fixture
def store():
    return make_store()


@pytest.fixture
def client():
    return FakeClient()


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def queue(store, client, storage):
    @asynccontextmanager
    async def uow_factory():
        yield MemUow(store)

    return AvGenerationQueue(
        uow_factory=uow_factory,
        client=client,
        storage=storage,
        runner=AsyncioTaskRunner(),
        reference_mode=lambda model: "multi" if model == "t2i-m" else "none",
        poll_interval=0.01,
    )


async def drain(queue: AvGenerationQueue, timeout: float = 5.0) -> None:
    async def _wait():
        while queue.active_count > 0:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_wait(), timeout)


async def test_image_success_saves_file_and_marks_shot(queue, store, storage):
    assert queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m") is True
    await drain(queue)
    shot = store["shots"][1]
    assert shot.asset_state(AssetKind.IMAGE) == AssetState.SUCCESS
    assert shot.image_path in storage.saved
    assert shot.image_version == 1


async def test_image_multi_mode_sends_all_covers_in_order(queue, store, client):
    store["shots"][1].ref_character_ids = [10, 12]
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    kind, prompt, model, ref = client.calls[0]
    assert ref == [b"cover-bytes", b"cover2-bytes"]
    assert "Momo is the character in reference image 1" in prompt
    assert "Kuku is the character in reference image 2" in prompt
    assert prompt.endswith("prompt 1")


async def test_image_multi_mode_falls_back_for_missing_cover(queue, store, client):
    store["shots"][1].ref_character_ids = [10, 11]
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    kind, prompt, model, ref = client.calls[0]
    assert ref == [b"cover-bytes"]
    assert "Momo is the character in reference image 1" in prompt
    assert "Lulu: a grey bunny." in prompt


async def test_image_none_mode_appearance_only(queue, store, client):
    store["shots"][1].ref_character_ids = [10, 12]
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-nref")
    await drain(queue)
    kind, prompt, model, ref = client.calls[0]
    assert ref is None
    assert "Momo: a cute fox." in prompt
    assert "Kuku: a small bear." in prompt
    assert prompt.endswith("prompt 1")


async def test_image_no_characters_sends_bare_prompt(queue, store, client):
    store["shots"][1].ref_character_ids = []
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    kind, prompt, model, ref = client.calls[0]
    assert ref is None
    assert prompt == "prompt 1"


async def test_concurrency_limit_two_images(queue, store, client):
    client.delay = 0.05
    for shot_id in (1, 2, 3, 4):
        queue.enqueue(1, shot_id, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    assert client.max_concurrent <= 2
    assert len(client.calls) == 4


async def test_duplicate_enqueue_rejected(queue, client):
    client.gate = asyncio.Event()
    assert queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m") is True
    assert queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m") is False
    client.gate.set()
    await drain(queue)


async def test_video_waits_for_image_then_succeeds(queue, store, client):
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    queue.enqueue(1, 1, AssetKind.VIDEO, "i2v-m")
    await drain(queue)
    shot = store["shots"][1]
    assert shot.asset_state(AssetKind.VIDEO) == AssetState.SUCCESS
    kinds = [c[0] for c in client.calls]
    assert kinds.index("image") < kinds.index("video")


async def test_video_fails_when_image_failed(queue, store, client):
    client.fail_kinds["image"] = ServerException(codes.AV_UPSTREAM_FAILED, "boom")
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    queue.enqueue(1, 1, AssetKind.VIDEO, "i2v-m")
    await drain(queue)
    shot = store["shots"][1]
    assert shot.asset_state(AssetKind.IMAGE) == AssetState.FAILED
    assert shot.asset_state(AssetKind.VIDEO) == AssetState.FAILED
    assert "分镜图" in shot.video_error


async def test_audio_success_records_duration_and_voice(queue, store, client):
    queue.enqueue(1, 2, AssetKind.AUDIO, "tts-m", voice="bella")
    await drain(queue)
    shot = store["shots"][2]
    assert shot.asset_state(AssetKind.AUDIO) == AssetState.SUCCESS
    assert shot.audio_duration == 3.3
    assert ("audio", "Line 2!", "tts-m", "bella") in client.calls


async def test_upstream_failure_marks_failed_with_error(queue, store, client):
    client.fail_kinds["audio"] = ServerException(codes.AV_UPSTREAM_FAILED, "tts 503")
    queue.enqueue(1, 1, AssetKind.AUDIO, "tts-m")
    await drain(queue)
    shot = store["shots"][1]
    assert shot.asset_state(AssetKind.AUDIO) == AssetState.FAILED
    assert "503" in shot.audio_error


async def test_quota_error_pauses_queue_and_restores_pending(queue, store, client):
    client.fail_kinds["image"] = ServerException(codes.AV_UPSTREAM_QUOTA, "余额不足")
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    assert queue.paused is True
    assert "余额" in (queue.paused_reason or "")
    shot = store["shots"][1]
    assert shot.asset_state(AssetKind.IMAGE) == AssetState.PENDING


async def test_cancel_project_drops_queued_items(queue, store, client):
    client.gate = asyncio.Event()
    queue.enqueue(1, 1, AssetKind.VIDEO, "i2v-m")  # 等图，不会开跑
    queue.enqueue(1, 2, AssetKind.VIDEO, "i2v-m")
    cancelled = queue.cancel_project(1)
    assert cancelled == 2
    client.gate.set()
    await drain(queue)
    assert len([c for c in client.calls if c[0] == "video"]) == 0
    assert store["shots"][1].asset_state(AssetKind.VIDEO) == AssetState.PENDING


async def test_success_stales_composed_project(queue, store):
    project = store["projects"][1]
    project.mark_compose_succeeded("projects/1/final.mp4")
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(queue)
    assert project.compose_state == ComposeState.SUCCESS
    assert project.compose_stale is True


async def test_counts_reports_project_queue(queue, store, client):
    client.gate = asyncio.Event()
    queue.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    queue.enqueue(1, 2, AssetKind.IMAGE, "t2i-m")
    queue.enqueue(1, 3, AssetKind.IMAGE, "t2i-m")
    await asyncio.sleep(0.05)
    pending, running = queue.counts(1)
    assert running == 2
    assert pending == 1
    client.gate.set()
    await drain(queue)


async def test_video_uses_video_prompt_and_duration(queue, store, client, storage):
    shot = store["shots"][1]
    shot.video_prompt = "waves at camera, slow push-in"
    shot.mark_running(AssetKind.IMAGE)
    shot.mark_succeeded(AssetKind.IMAGE, path="projects/1/shots/1/image.png")
    storage.saved["projects/1/shots/1/image.png"] = b"img"
    queue.enqueue(1, 1, AssetKind.VIDEO, "i2v-m")
    await drain(queue)
    call = next(c for c in client.calls if c[0] == "video")
    assert call[1] == "waves at camera, slow push-in"
    assert call[3] == round(shot.duration_estimate)


async def test_video_falls_back_to_image_prompt(queue, store, client, storage):
    shot = store["shots"][1]
    shot.mark_running(AssetKind.IMAGE)
    shot.mark_succeeded(AssetKind.IMAGE, path="projects/1/shots/1/image.png")
    storage.saved["projects/1/shots/1/image.png"] = b"img"
    queue.enqueue(1, 1, AssetKind.VIDEO, "i2v-m")
    await drain(queue)
    call = next(c for c in client.calls if c[0] == "video")
    assert call[1] == "prompt 1"


async def test_upstream_call_happens_outside_uow(store, client, storage):
    """上游生成（可长达 10 分钟）期间不得占用数据库会话/事务。"""
    state = {"open": 0}

    @asynccontextmanager
    async def uow_factory():
        state["open"] += 1
        try:
            yield MemUow(store)
        finally:
            state["open"] -= 1

    orig = client._work
    seen = {}

    async def patched(kind, *args):
        seen["open_during_call"] = state["open"]
        return await orig(kind, *args)

    client._work = patched
    q = AvGenerationQueue(
        uow_factory=uow_factory,
        client=client,
        storage=storage,
        runner=AsyncioTaskRunner(),
        reference_mode=lambda m: "none",
        poll_interval=0.01,
    )
    q.enqueue(1, 1, AssetKind.IMAGE, "t2i-m")
    await drain(q)
    assert seen["open_during_call"] == 0
