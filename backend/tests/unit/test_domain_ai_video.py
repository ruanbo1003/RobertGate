"""AI Videos 领域模型单元测试：实体校验、产物状态机、过期链、拆分镜纯函数。"""

from __future__ import annotations

import pytest

from app.domain.errors import ParamException
from app.domain.models.ai_video import (
    AssetKind,
    AssetState,
    AvCharacter,
    AvProject,
    AvShot,
    ComposeState,
    derive_project_status,
    estimate_duration,
    missing_compose_items,
    shots_from_script,
    stale_items,
    validate_script,
)

DEFAULT_MODELS = {
    "llm": "deepseek-ai/DeepSeek-V3",
    "t2i": "Kwai-Kolors/Kolors",
    "i2v": "Wan-AI/Wan2.2-I2V-A14B",
    "tts": "FunAudioLLM/CosyVoice2-0.5B",
}


def _shot(order: int = 1, line: str = "Hello!") -> AvShot:
    return AvShot.create(
        project_id=1,
        order_index=order,
        speaker_character_id=1,
        ref_character_ids=[1],
        line_en=line,
        line_zh="你好！",
        image_prompt="a fox waving, picture book style",
        models=DEFAULT_MODELS,
        tts_voice="alex",
    )


def _project() -> AvProject:
    return AvProject.create(
        title="EP01 · Hello",
        synopsis="打招呼",
        target_duration=60,
        default_models=DEFAULT_MODELS,
        tts_voice="alex",
    )


# ---------------- 实体校验 ----------------


class TestCharacterValidation:
    def test_create_normalizes_fields(self):
        c = AvCharacter.create(name="  Momo ", appearance_prompt=" a fox ", personality=None)
        assert c.name == "Momo"
        assert c.appearance_prompt == "a fox"
        assert c.personality is None

    def test_empty_name_rejected(self):
        with pytest.raises(ParamException):
            AvCharacter.create(name="  ", appearance_prompt="a fox", personality=None)

    def test_overlong_appearance_rejected(self):
        with pytest.raises(ParamException):
            AvCharacter.create(name="Momo", appearance_prompt="x" * 1001, personality=None)


class TestProjectValidation:
    def test_create_defaults(self):
        p = _project()
        assert p.compose_state == ComposeState.NONE
        assert p.script is None
        assert p.compose_stale is False

    def test_duration_out_of_range_rejected(self):
        for bad in (29, 121):
            with pytest.raises(ParamException):
                AvProject.create(
                    title="t",
                    synopsis="s",
                    target_duration=bad,
                    default_models=DEFAULT_MODELS,
                    tts_voice="alex",
                )

    def test_empty_title_rejected(self):
        with pytest.raises(ParamException):
            AvProject.create(
                title=" ",
                synopsis="s",
                target_duration=60,
                default_models=DEFAULT_MODELS,
                tts_voice="alex",
            )


# ---------------- 产物状态机 ----------------


class TestAssetStateMachine:
    def test_new_shot_assets_pending(self):
        s = _shot()
        for kind in AssetKind:
            assert s.asset_state(kind) == AssetState.PENDING
            assert s.asset_version(kind) == 0

    def test_success_bumps_version_and_clears_stale(self):
        s = _shot()
        s.mark_running(AssetKind.IMAGE)
        assert s.asset_state(AssetKind.IMAGE) == AssetState.RUNNING
        s.mark_succeeded(AssetKind.IMAGE, path="p/1.png")
        assert s.asset_state(AssetKind.IMAGE) == AssetState.SUCCESS
        assert s.image_path == "p/1.png"
        assert s.asset_version(AssetKind.IMAGE) == 1
        assert s.image_stale is False
        assert s.image_error is None

    def test_failed_records_error(self):
        s = _shot()
        s.mark_running(AssetKind.VIDEO)
        s.mark_failed(AssetKind.VIDEO, "timeout (504)")
        assert s.asset_state(AssetKind.VIDEO) == AssetState.FAILED
        assert s.video_error == "timeout (504)"

    def test_audio_success_records_duration(self):
        s = _shot()
        s.mark_running(AssetKind.AUDIO)
        s.mark_succeeded(AssetKind.AUDIO, path="p/a.mp3", audio_duration=3.4)
        assert s.audio_duration == 3.4


# ---------------- 过期链 ----------------


class TestStaleChain:
    def _succeed_all(self, s: AvShot) -> None:
        for kind in AssetKind:
            s.mark_running(kind)
            s.mark_succeeded(kind, path=f"p/{kind.value}")

    def test_prompt_change_stales_image_and_video(self):
        s = _shot()
        self._succeed_all(s)
        staled = s.apply_patch(image_prompt="new prompt")
        assert set(staled) == {AssetKind.IMAGE, AssetKind.VIDEO}
        assert s.image_stale and s.video_stale and not s.audio_stale

    def test_ref_character_ids_change_stales_image_and_video(self):
        s = _shot()
        self._succeed_all(s)
        staled = s.apply_patch(ref_character_ids=[2, 1])
        assert set(staled) == {AssetKind.IMAGE, AssetKind.VIDEO}

    def test_video_prompt_change_stales_video_only(self):
        s = _shot()
        self._succeed_all(s)
        staled = s.apply_patch(video_prompt="waves at camera, slow push-in")
        assert set(staled) == {AssetKind.VIDEO}
        assert s.video_stale and not s.image_stale and not s.audio_stale

    def test_line_change_stales_audio_only(self):
        s = _shot()
        self._succeed_all(s)
        staled = s.apply_patch(line_en="New line!")
        assert set(staled) == {AssetKind.AUDIO}
        assert s.audio_stale and not s.image_stale

    def test_unchanged_value_does_not_stale(self):
        s = _shot()
        self._succeed_all(s)
        staled = s.apply_patch(image_prompt=s.image_prompt)
        assert staled == []
        assert not s.image_stale

    def test_pending_asset_not_staled(self):
        s = _shot()  # 全部 pending
        staled = s.apply_patch(image_prompt="new")
        assert staled == []
        assert not s.image_stale

    def test_regenerate_success_clears_stale(self):
        s = _shot()
        self._succeed_all(s)
        s.apply_patch(line_en="New line!")
        assert s.audio_stale
        s.mark_running(AssetKind.AUDIO)
        s.mark_succeeded(AssetKind.AUDIO, path="p/a2.mp3", audio_duration=2.0)
        assert not s.audio_stale
        assert s.asset_version(AssetKind.AUDIO) == 2


# ---------------- 剧本校验与拆分镜 ----------------


VALID_SCRIPT = {
    "scenes": [
        {
            "setting": "At the park",
            "lines": [
                {"character_id": 1, "en": "Hi Kuku!", "zh": "嗨 Kuku！"},
                {"character_id": 3, "en": "Let's play together now!", "zh": "一起玩吧！"},
            ],
        }
    ]
}


class TestScript:
    def test_validate_script_passes_valid(self):
        script = validate_script(VALID_SCRIPT)
        assert len(script["scenes"][0]["lines"]) == 2

    def test_validate_script_rejects_empty_scenes(self):
        with pytest.raises(ParamException):
            validate_script({"scenes": []})

    def test_validate_script_rejects_missing_en(self):
        bad = {"scenes": [{"setting": "x", "lines": [{"character_id": 1, "zh": "嗨"}]}]}
        with pytest.raises(ParamException):
            validate_script(bad)

    def test_estimate_duration_clamped(self):
        assert estimate_duration("Hi!") == 3.0
        assert estimate_duration(" ".join(["word"] * 30)) == 6.0
        mid = estimate_duration("I want to buy apples today")  # 6 词
        assert 3.0 < mid < 6.0

    def test_validate_script_passes_optional_fields(self):
        s = validate_script(
            {
                "scenes": [
                    {
                        "setting": "park",
                        "lines": [
                            {
                                "character_id": 1,
                                "en": "Hi!",
                                "zh": "嗨",
                                "video_prompt": "waves, push-in",
                                "characters": ["Max", " Dog ", ""],
                            }
                        ],
                    }
                ]
            }
        )
        line = s["scenes"][0]["lines"][0]
        assert line["video_prompt"] == "waves, push-in"
        assert line["characters"] == ["Max", "Dog"]

    def test_validate_script_defaults_optional_fields(self):
        s = validate_script(VALID_SCRIPT)
        line = s["scenes"][0]["lines"][0]
        assert line["video_prompt"] == ""
        assert line["characters"] == []

    def test_shots_from_script_builds_ordered_shots(self):
        shots = shots_from_script(
            project_id=7,
            script=VALID_SCRIPT,
            appearance_of=lambda cid: {1: "a fox", 3: "a bear"}.get(cid),
            models=DEFAULT_MODELS,
            tts_voice="alex",
            resolve_character=lambda name: None,
        )
        assert [s.order_index for s in shots] == [1, 2]
        assert shots[0].project_id == 7
        assert shots[0].speaker_character_id == 1
        # characters 缺省 → 回退说话人
        assert shots[0].ref_character_ids == [1]
        assert shots[0].video_prompt == ""
        assert shots[0].line_en == "Hi Kuku!"
        # 画面 prompt 融合了角色外形与场景
        assert "a fox" in shots[0].image_prompt
        assert "At the park" in shots[0].image_prompt
        for s in shots:
            assert s.asset_state(AssetKind.IMAGE) == AssetState.PENDING

    def test_shots_from_script_resolves_characters_and_falls_back(self):
        script = {
            "scenes": [
                {
                    "setting": "park",
                    "lines": [
                        {
                            "character_id": 1,
                            "en": "Hi!",
                            "zh": "嗨",
                            "video_prompt": "both wave, camera static",
                            "characters": ["Max", "Ghost", "Max"],
                        }
                    ],
                }
            ]
        }
        shots = shots_from_script(
            project_id=7,
            script=script,
            appearance_of=lambda cid: "a fox",
            models=DEFAULT_MODELS,
            tts_voice="alex",
            resolve_character=lambda name: {"max": 7}.get(name.lower()),
        )
        # Ghost 解析不到被忽略，Max 去重保序
        assert shots[0].ref_character_ids == [7]
        assert shots[0].video_prompt == "both wave, camera static"


# ---------------- 聚合与合成校验 ----------------


class TestAggregation:
    def test_status_draft_when_no_shots(self):
        assert derive_project_status([], queue_active=False) == "draft"

    def test_status_generating_when_queue_active(self):
        assert derive_project_status([_shot()], queue_active=True) == "generating"

    def test_status_generating_when_any_running(self):
        s = _shot()
        s.mark_running(AssetKind.IMAGE)
        assert derive_project_status([s], queue_active=False) == "generating"

    def test_status_partial_failed(self):
        s = _shot()
        s.mark_running(AssetKind.IMAGE)
        s.mark_failed(AssetKind.IMAGE, "boom")
        assert derive_project_status([s], queue_active=False) == "partial_failed"

    def test_status_completed_when_all_success(self):
        s = _shot()
        for kind in AssetKind:
            s.mark_running(kind)
            s.mark_succeeded(kind, path="p")
        assert derive_project_status([s], queue_active=False) == "completed"

    def test_missing_compose_items_only_video_audio(self):
        s = _shot()
        s.mark_running(AssetKind.IMAGE)
        s.mark_succeeded(AssetKind.IMAGE, path="p")
        items = missing_compose_items([s])
        kinds = {i["kind"] for i in items}
        assert kinds == {"video", "audio"}

    def test_stale_items_lists_all_kinds(self):
        s = _shot()
        for kind in AssetKind:
            s.mark_running(kind)
            s.mark_succeeded(kind, path="p")
        s.apply_patch(image_prompt="new", line_en="new line")
        items = stale_items([s])
        assert {i["kind"] for i in items} == {"image", "video", "audio"}
        assert all(i["shot_order"] == s.order_index for i in items)
