"""AvCharacterService / AvProjectService 业务规则单元测试（FakeUow + mock 协作者）。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.av_service import AvCharacterService, AvProjectService
from app.domain.errors import ParamException, codes
from app.domain.models.ai_video import (
    AssetKind,
    AvCharacter,
    AvCharacterImage,
    AvProject,
    AvProjectCharacter,
    AvShot,
    ComposeState,
)

DEFAULT_MODELS = {
    "llm": "llm-m",
    "t2i": "t2i-m",
    "i2v": "i2v-m",
    "tts": "tts-m",
}


def _character(id_: int = 1, name: str = "Momo") -> AvCharacter:
    c = AvCharacter.create(name=name, appearance_prompt="a cute fox", personality=None)
    c.id = id_
    return c


def _project(id_: int = 1) -> AvProject:
    p = AvProject.create(
        title="EP01",
        synopsis="s",
        target_duration=60,
        default_models=DEFAULT_MODELS,
        tts_voice="alex",
    )
    p.id = id_
    return p


def _shot(id_: int = 1, order: int = 1, project_id: int = 1) -> AvShot:
    s = AvShot.create(
        project_id=project_id,
        order_index=order,
        speaker_character_id=1,
        ref_character_ids=[1],
        line_en=f"Line {order}!",
        line_zh="",
        image_prompt=f"prompt {order}",
        models=DEFAULT_MODELS,
        tts_voice="alex",
    )
    s.id = id_
    return s


class FakeStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def save(self, rel_path: str, data: bytes) -> str:
        self.saved[rel_path] = data
        return rel_path

    def read(self, rel_path: str) -> bytes:
        return self.saved.get(rel_path, b"")

    async def probe_duration(self, rel_path: str) -> float | None:
        return 2.5

    def delete(self, rel_path: str) -> None:
        self.deleted.append(rel_path)

    def delete_tree(self, rel_dir: str) -> None:
        self.deleted.append(rel_dir)

    def absolute(self, rel_path: str):
        from pathlib import Path

        return Path("/data") / rel_path


class FakeRunner:
    def __init__(self):
        self.coros = []

    def spawn(self, coro):
        self.coros.append(coro)


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client():
    c = AsyncMock()
    c.generate_image = AsyncMock(return_value=b"img")
    c.generate_json = AsyncMock(
        return_value={
            "scenes": [
                {
                    "setting": "park",
                    "lines": [{"character_id": 1, "en": "Hi!", "zh": "嗨"}],
                }
            ]
        }
    )
    return c


@pytest.fixture
def queue(uow):
    q = MagicMock()
    q.is_active = MagicMock(return_value=False)
    q.enqueue = MagicMock(side_effect=lambda *a, **k: uow.calls.append("enqueue") or True)
    q.cancel_project = MagicMock(return_value=0)
    q.counts = MagicMock(return_value=(0, 0))
    q.paused = False
    q.paused_reason = None
    return q


@pytest.fixture
def runner():
    return FakeRunner()


@pytest.fixture
def char_service(uow, client, storage):
    return AvCharacterService(uow=uow, client=client, storage=storage)


@pytest.fixture
def composer():
    c = AsyncMock()
    c.compose = AsyncMock()
    return c


@pytest.fixture
def project_service(uow, client, queue, storage, composer, runner):
    @asynccontextmanager
    async def uow_factory():
        yield uow

    return AvProjectService(
        uow=uow,
        client=client,
        queue=queue,
        storage=storage,
        composer=composer,
        runner=runner,
        uow_factory=uow_factory,
    )


# ---------------- 角色 ----------------


async def test_create_character_rejects_duplicate_name(char_service, uow):
    uow.av_characters.find_by_name = AsyncMock(return_value=_character())
    with pytest.raises(ParamException) as e:
        await char_service.create_character("Momo", "a fox", None)
    assert e.value.code == codes.AV_PARAM_INVALID


async def test_delete_character_in_use_carries_references(char_service, uow):
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    uow.av_project_characters.list_by_character = AsyncMock(
        return_value=[AvProjectCharacter(project_id=3, character_id=1)]
    )
    uow.av_projects.find_by_id = AsyncMock(return_value=_project(3))
    with pytest.raises(ParamException) as e:
        await char_service.delete_character(1)
    assert e.value.code == codes.AV_CHARACTER_IN_USE
    assert e.value.data["used_by"][0]["project_id"] == 3


async def test_generate_character_image_caps_candidates(char_service, uow, storage):
    char = _character()
    char.cover_image_id = 101
    existing = [AvCharacterImage(id=100 + i, character_id=1, path=f"characters/1/{i}.png") for i in range(8)]
    uow.av_characters.find_by_id = AsyncMock(return_value=char)
    uow.av_character_images.list_by_character = AsyncMock(return_value=existing)
    out = await char_service.generate_image(1, model="t2i-m", prompt=None)
    assert out.url.startswith("/api/v1/ai-videos/files/")
    # 超限：淘汰最旧的非封面候选（id=100 是封面 101 之外最旧的 → id=100 不是封面，被删）
    deleted_ids = [c for c in uow.calls if c == "av_character_images.delete"]
    assert len(deleted_ids) == 1
    assert uow.commit.await_count == 1


# ---------------- 项目 / 剧本 / 分镜 ----------------


async def test_create_project_rejects_unknown_character(project_service, uow):
    uow.av_characters.find_by_id = AsyncMock(return_value=None)
    with pytest.raises(ParamException) as e:
        await project_service.create_project(
            title="t",
            synopsis="s",
            character_ids=[99],
            target_duration=60,
            default_models=None,
            tts_voice=None,
        )
    assert e.value.code == codes.AV_PARAM_INVALID


async def test_generate_script_saves_validated_script(project_service, uow, client):
    project = _project()
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_project_characters.list_by_project = AsyncMock(
        return_value=[AvProjectCharacter(project_id=1, character_id=1)]
    )
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    script = await project_service.generate_script(1, model=None)
    assert project.script is not None
    assert script["scenes"][0]["lines"][0]["en"] == "Hi!"
    assert uow.commit.await_count == 1


async def test_split_shots_requires_confirm_when_shots_exist(project_service, uow):
    project = _project()
    project.script = {"scenes": [{"setting": "p", "lines": [{"character_id": 1, "en": "Hi!", "zh": ""}]}]}
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[_shot()])
    with pytest.raises(ParamException) as e:
        await project_service.split_shots(1, model=None, confirm_replace=False)
    assert e.value.code == codes.AV_SHOTS_CONFIRM_REQUIRED
    assert e.value.data["existing_shot_count"] == 1


async def test_split_shots_with_confirm_replaces_and_cancels_queue(
    project_service, uow, queue
):
    project = _project()
    project.script = {"scenes": [{"setting": "p", "lines": [{"character_id": 1, "en": "Hi!", "zh": ""}]}]}
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[_shot()])
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    shots = await project_service.split_shots(1, model=None, confirm_replace=True)
    assert len(shots) == 1
    queue.cancel_project.assert_called_once_with(1)
    uow.av_shots.delete_by_project.assert_awaited_once_with(1)


async def test_generate_video_requires_image_success(project_service, uow):
    shot = _shot()
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    with pytest.raises(ParamException) as e:
        await project_service.generate_asset(1, 1, AssetKind.VIDEO, model=None, voice=None)
    assert e.value.code == codes.AV_PRECONDITION_FAILED


async def test_generate_asset_rejected_when_queue_busy(project_service, uow, queue):
    shot = _shot()
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    queue.is_active = MagicMock(return_value=True)
    with pytest.raises(ParamException) as e:
        await project_service.generate_asset(1, 1, AssetKind.IMAGE, model=None, voice=None)
    assert e.value.code == codes.AV_ASSET_BUSY


async def test_generate_asset_commits_before_enqueue(project_service, uow, queue):
    shot = _shot()
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    await project_service.generate_asset(1, 1, AssetKind.IMAGE, model=None, voice=None)
    assert "commit" in uow.calls and "enqueue" in uow.calls
    assert uow.calls.index("commit") < uow.calls.index("enqueue")
    assert shot.image_state == "pending"


async def test_generate_all_missing_scope_skips_fresh_success(project_service, uow, queue):
    s1, s2 = _shot(1, 1), _shot(2, 2)
    s1.mark_running(AssetKind.IMAGE)
    s1.mark_succeeded(AssetKind.IMAGE, path="p")  # 新鲜成功 → 跳过
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[s1, s2])
    enqueued = await project_service.generate_all(1, types=[AssetKind.IMAGE], scope="missing")
    assert enqueued["image"] == 1  # 只有 s2


# ---------------- 合成 ----------------


def _ready_shot(id_: int, order: int) -> AvShot:
    s = _shot(id_, order)
    for kind in AssetKind:
        s.mark_running(kind)
        s.mark_succeeded(kind, path=f"projects/1/shots/{id_}/{kind.value}", audio_duration=2.0)
    return s


async def test_compose_rejects_missing_assets(project_service, uow):
    shot = _shot()  # 全 pending
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    with pytest.raises(ParamException) as e:
        await project_service.compose(1, ignore_stale=False)
    assert e.value.code == codes.AV_PRECONDITION_FAILED
    assert len(e.value.data["missing"]) == 2


async def test_compose_requires_stale_confirm(project_service, uow):
    shot = _ready_shot(1, 1)
    shot.apply_patch(line_en="changed")  # audio stale
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    with pytest.raises(ParamException) as e:
        await project_service.compose(1, ignore_stale=False)
    assert e.value.code == codes.AV_STALE_CONFIRM_REQUIRED
    assert e.value.data["stale_items"][0]["kind"] == "audio"


async def test_compose_spawns_background_task_after_commit(
    project_service, uow, runner, composer
):
    project = _project()
    shot = _ready_shot(1, 1)
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    await project_service.compose(1, ignore_stale=True)
    assert project.compose_state == ComposeState.RUNNING
    assert uow.commit.await_count == 1
    assert len(runner.coros) == 1
    # 跑后台协程：合成成功落库
    await runner.coros[0]
    composer.compose.assert_awaited_once()
    assert project.compose_state == ComposeState.SUCCESS
    assert project.compose_path == "projects/1/final.mp4"
