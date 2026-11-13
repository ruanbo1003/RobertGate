"""AvCharacterService / AvProjectService 业务规则单元测试（FakeUow + mock 协作者）。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.dto.ai_video import CharacterOut, ShotOut
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
        ref_character_ids=[1],
        dialogue=[{"character_id": 1, "en": f"Line {order}!", "zh": ""}],
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
    c.probe_duration = AsyncMock(return_value=None)  # 回退 shot.duration_estimate
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


# ---------------- API 契约（DTO） ----------------


class TestShotOutContract:
    def test_dialogue_shot_has_no_audio_block_and_correct_dialogue_length(self):
        shot = _shot()  # dialogue 非空（_shot 默认单句）
        out = ShotOut.build(shot)
        assert out.audio is None
        assert len(out.dialogue) == 1
        assert out.dialogue[0].en == "Line 1!"

    def test_plain_shot_without_dialogue_has_audio_block(self):
        shot = AvShot.create(
            project_id=1, order_index=1, ref_character_ids=[],
            dialogue=[], image_prompt="p", models=DEFAULT_MODELS, tts_voice="alex",
        )
        out = ShotOut.build(shot)
        assert out.audio is not None
        assert out.dialogue == []


class TestCharacterOutContract:
    def test_voice_desc_surfaces_in_character_out(self):
        char = _character()
        char.apply_update(name=None, appearance_prompt=None, personality=None,
                           voice_desc="warm friendly")
        out = CharacterOut.build(char, [], used_count=0)
        assert out.voice_desc == "warm friendly"


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


async def test_split_shots_merges_consecutive_lines_into_one_dialogue_shot(
    project_service, uow
):
    project = _project()
    project.script = {
        "scenes": [
            {
                "setting": "park",
                "lines": [
                    {"character_id": 1, "en": "Hello Lily", "zh": ""},
                    {"character_id": 2, "en": "Hi Max", "zh": ""},
                ],
            }
        ]
    }
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[])
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    shots = await project_service.split_shots(1, model=None, confirm_replace=False)
    assert len(shots) == 1
    added_shots = [c.args[0] for c in uow.av_shots.add.call_args_list]
    assert [ln["en"] for ln in added_shots[0].dialogue] == ["Hello Lily", "Hi Max"]


async def test_create_shot_builds_blank_shot_without_dialogue(project_service, uow):
    project = _project()
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[])
    await project_service.create_shot(1, after_shot_id=None)
    added_shot = uow.av_shots.add.call_args[0][0]
    assert added_shot.dialogue == []
    assert added_shot.ref_character_ids == []


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


async def test_generate_asset_audio_rejected_for_dialogue_shot(project_service, uow):
    shot = _shot()  # _shot() 自带 dialogue 非空
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    with pytest.raises(ParamException) as e:
        await project_service.generate_asset(1, 1, AssetKind.AUDIO, model=None, voice=None)
    assert e.value.code == codes.AV_PARAM_INVALID


async def test_generate_all_skips_audio_for_dialogue_shots(project_service, uow, queue):
    shot = _shot()  # has_dialogue
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    enqueued = await project_service.generate_all(1, types=[AssetKind.AUDIO], scope="all")
    assert enqueued["audio"] == 0


async def test_generate_all_skips_audio_for_legacy_migrated_dialogue_shot(
    project_service, uow, queue
):
    # 0010 迁移回填：旧字段 line_en 留存未清空，但 dialogue 已非空——必须按 dialogue 判定
    shot = _shot()
    shot.line_en = "Old leftover line"
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    enqueued = await project_service.generate_all(1, types=[AssetKind.AUDIO], scope="all")
    assert enqueued["audio"] == 0


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
    # audio 产物不再参与合成预检，只缺 video
    assert [m["kind"] for m in e.value.data["missing"]] == ["video"]


async def test_compose_requires_stale_confirm(project_service, uow):
    shot = _ready_shot(1, 1)
    shot.apply_patch(dialogue=[{"character_id": 1, "en": "changed", "zh": ""}])  # video stale
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    with pytest.raises(ParamException) as e:
        await project_service.compose(1, ignore_stale=False)
    assert e.value.code == codes.AV_STALE_CONFIRM_REQUIRED
    assert e.value.data["stale_items"][0]["kind"] == "video"


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


class FakeWhisperAligner:
    def __init__(self, words: list[tuple[str, float, float]]):
        self.words = words
        self.calls: list = []

    def transcribe_words(self, media):
        self.calls.append(media)
        return self.words


async def _dialogue_ready_shot(id_: int, order: int) -> AvShot:
    s = _shot(id_, order)  # dialogue=[{"character_id":1,"en":f"Line {order}!","zh":""}]
    s.mark_running(AssetKind.IMAGE)
    s.mark_succeeded(AssetKind.IMAGE, path=f"projects/1/shots/{id_}/image")
    s.mark_running(AssetKind.VIDEO)
    s.mark_succeeded(AssetKind.VIDEO, path=f"projects/1/shots/{id_}/video")
    return s  # audio_path 留空：有声对白镜，走 whisper 对齐


async def test_compose_dialogue_shot_without_audio_uses_whisper_alignment(
    project_service, uow, runner, composer
):
    shot = await _dialogue_ready_shot(1, 1)
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    whisper = FakeWhisperAligner([("Line", 0.0, 1.0), ("1!", 1.0, shot.duration_estimate)])
    project_service._whisper = whisper
    await project_service.compose(1, ignore_stale=True)
    await runner.coros[0]
    composer.compose.assert_awaited_once()
    items = composer.compose.call_args[0][0]
    assert len(items) == 1
    assert items[0].audio is None
    assert whisper.calls == [items[0].video]
    assert items[0].subtitles == [("Line 1!", 0.0, shot.duration_estimate)]


async def test_compose_aligns_on_english_text_even_when_zh_present(
    project_service, uow, runner, composer
):
    # 终审发现：对齐 key 曾经用 "en\nzh" 整句，中文字符被当 token 计入总数，
    # whisper 只能匹配英文词，匹配率结构性地必然 <50% → 永远回退均分。
    # 用两句话区分"真实对齐"与"均分"：均分会把中点切在 total/2，真实对齐
    # 会切在词时间戳的实际边界上——两者在本用例下数值不同，足以证伪回退。
    shot = _shot()
    shot.dialogue = [
        {"character_id": 1, "en": "Hello Lily!", "zh": "你好，莉莉！"},
        {"character_id": 2, "en": "Hi Max, how are you?", "zh": "嗨，麦克斯，你好吗？"},
    ]
    shot.duration_estimate = 10.0
    shot.mark_running(AssetKind.IMAGE)
    shot.mark_succeeded(AssetKind.IMAGE, path="p/i")
    shot.mark_running(AssetKind.VIDEO)
    shot.mark_succeeded(AssetKind.VIDEO, path="p/v")
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    whisper = FakeWhisperAligner([
        ("Hello", 0.0, 0.5), ("Lily", 0.5, 1.0),
        ("Hi", 1.2, 1.5), ("Max", 1.5, 1.8), ("how", 1.8, 2.0), ("are", 2.0, 2.2), ("you", 2.2, 2.5),
    ])
    project_service._whisper = whisper
    await project_service.compose(1, ignore_stale=True)
    await runner.coros[0]
    items = composer.compose.call_args[0][0]
    subs = items[0].subtitles
    assert subs[0] == ("Hello Lily!\n你好，莉莉！", 0.0, 1.0)
    # 第二句开始于词时间戳 1.2（真实对齐），均分会是 5.0——数值上可区分
    assert subs[1][0] == "Hi Max, how are you?\n嗨，麦克斯，你好吗？"
    assert subs[1][1] == 1.2
    assert subs[1][2] == 10.0  # 末句延伸到镜尾


class _ExplodingWhisperAligner:
    def transcribe_words(self, media):
        raise RuntimeError("ffmpeg 解码失败（模拟 whisper 执行层异常）")


async def test_compose_whisper_exception_falls_back_instead_of_failing_compose(
    project_service, uow, runner, composer
):
    # 终审发现：whisper 异常此前会冒泡炸掉整次合成；回退应让合成照常成功。
    shot = await _dialogue_ready_shot(1, 1)
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[shot])
    project_service._whisper = _ExplodingWhisperAligner()
    await project_service.compose(1, ignore_stale=True)
    await runner.coros[0]
    composer.compose.assert_awaited_once()
    items = composer.compose.call_args[0][0]
    assert len(items[0].subtitles) == 1  # 回退均分，字幕不缺席


async def test_compose_mixed_mux_and_dialogue_shots(project_service, uow, runner, composer):
    mux_shot = _ready_shot(1, 1)  # _ready_shot 生成全部产物，含物理 audio 文件
    dialogue_shot = await _dialogue_ready_shot(2, 2)
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.list_by_project = AsyncMock(return_value=[mux_shot, dialogue_shot])
    project_service._whisper = FakeWhisperAligner([])  # 空词 → 对白镜回退均分
    await project_service.compose(1, ignore_stale=True)
    await runner.coros[0]
    items = composer.compose.call_args[0][0]
    assert len(items) == 2
    assert items[0].audio is not None  # mux 镜
    assert items[1].audio is None  # 对白镜


# ---------------- Task 5: video_prompt / 出场角色 ----------------


def test_script_system_requires_video_prompt_and_characters():
    from app.application.services.av_service import _SCRIPT_SYSTEM

    assert '"image_prompt"' in _SCRIPT_SYSTEM
    assert '"video_prompt"' in _SCRIPT_SYSTEM
    assert '"characters"' in _SCRIPT_SYSTEM


async def test_update_shot_rejects_ref_character_outside_project(project_service, uow):
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=_shot())
    uow.av_project_characters.list_by_project = AsyncMock(
        return_value=[AvProjectCharacter(project_id=1, character_id=1)]
    )
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    with pytest.raises(ParamException) as e:
        await project_service.update_shot(1, 1, {"ref_character_ids": [1, 99]})
    assert e.value.code == codes.AV_PARAM_INVALID


async def test_update_shot_accepts_valid_ref_characters_and_stales(project_service, uow):
    shot = _shot()
    for kind in AssetKind:
        shot.mark_running(kind)
        shot.mark_succeeded(kind, path=f"p/{kind.value}")
    uow.av_projects.find_by_id = AsyncMock(return_value=_project())
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    uow.av_project_characters.list_by_project = AsyncMock(
        return_value=[
            AvProjectCharacter(project_id=1, character_id=1),
            AvProjectCharacter(project_id=1, character_id=2),
        ]
    )
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    out = await project_service.update_shot(1, 1, {"ref_character_ids": [2, 1]})
    assert out["shot"].ref_character_ids == [2, 1]
    assert shot.image_stale and shot.video_stale


async def test_split_shots_resolves_names_and_video_prompt(project_service, uow, queue):
    project = _project()
    project.script = {
        "scenes": [
            {
                "setting": "p",
                "lines": [
                    {
                        "character_id": 1,
                        "en": "Hi!",
                        "zh": "",
                        "video_prompt": "waves, push-in",
                        "characters": ["momo", "Ghost"],
                    }
                ],
            }
        ]
    }
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.list_by_project = AsyncMock(return_value=[])
    uow.av_project_characters.list_by_project = AsyncMock(
        return_value=[AvProjectCharacter(project_id=1, character_id=1)]
    )
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    shots = await project_service.split_shots(1, model=None, confirm_replace=False)
    assert shots[0].video_prompt == "waves, push-in"
    assert shots[0].ref_character_ids == [1]


# ---------------- 活配置回退（kie 迁移：老项目失效模型读取时回退新默认） ----------------


@pytest.fixture
def strict_service(uow, client, queue, storage, composer, runner):
    """按生产 deps 的方式装配：model_known 用真注册表判据。"""
    from app.infrastructure.data.av_models import default_model, is_known_model

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
        model_defaults={t: default_model(t) for t in ("llm", "t2i", "i2v", "tts")},
        model_known=is_known_model,
    )


async def test_legacy_project_default_model_falls_back_to_new_default(strict_service, uow):
    # 老项目存的是已死的 OpenRouter 闭源模型 id：不回退则每次生成必失败
    from app.infrastructure.data.av_models import default_model

    project = _project()
    project.default_models = {**DEFAULT_MODELS, "t2i": "google/gemini-3.1-flash-image"}
    shot = _shot()
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    await strict_service.generate_asset(1, 1, AssetKind.IMAGE, model=None, voice=None)
    assert shot.image_model == default_model("t2i")


async def test_legacy_llm_model_falls_back_for_script(strict_service, uow, client):
    from app.infrastructure.data.av_models import default_model

    project = _project()
    project.default_models = {**DEFAULT_MODELS, "llm": "google/gemini-3.8-flash"}
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_project_characters.list_by_project = AsyncMock(
        return_value=[AvProjectCharacter(project_id=1, character_id=1)]
    )
    uow.av_characters.find_by_id = AsyncMock(return_value=_character())
    await strict_service.generate_script(1, model=None)
    assert client.generate_json.await_args.args[2] == default_model("llm")


async def test_known_model_is_used_as_is(strict_service, uow):
    from app.infrastructure.data.av_models import default_model

    project = _project()
    project.default_models = {**DEFAULT_MODELS, "t2i": "seedream/5-5-text-to-image"}
    shot = _shot()
    uow.av_projects.find_by_id = AsyncMock(return_value=project)
    uow.av_shots.find_by_id = AsyncMock(return_value=shot)
    await strict_service.generate_asset(1, 1, AssetKind.IMAGE, model=None, voice=None)
    # 用户选的省钱档合法 → 原样使用，不被"回退"冲掉
    assert shot.image_model == "seedream/5-5-text-to-image"
    assert shot.image_model != default_model("t2i")
