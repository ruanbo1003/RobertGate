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
    estimate_dialogue_duration,
    estimate_duration,
    group_script_into_shots,
    legacy_shot_to_dialogue,
    missing_compose_items,
    shots_from_script,
    stale_items,
    validate_dialogue,
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
        ref_character_ids=[1],
        dialogue=[{"character_id": 1, "en": line, "zh": "你好！"}],
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

    def test_create_defaults_voice_desc_empty(self):
        c = AvCharacter.create(name="Momo", appearance_prompt="a fox", personality=None)
        assert c.voice_desc == ""

    def test_create_accepts_voice_desc(self):
        c = AvCharacter.create(
            name="Momo", appearance_prompt="a fox", personality=None,
            voice_desc=" warm friendly ",
        )
        assert c.voice_desc == "warm friendly"


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
        s.apply_patch(video_prompt="new motion")
        assert s.video_stale
        s.mark_running(AssetKind.VIDEO)
        s.mark_succeeded(AssetKind.VIDEO, path="p/v2.mp4")
        assert not s.video_stale
        assert s.asset_version(AssetKind.VIDEO) == 2


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
                                "image_prompt": " Max waves at the park gate ",
                                "characters": ["Max", " Dog ", ""],
                            }
                        ],
                    }
                ]
            }
        )
        line = s["scenes"][0]["lines"][0]
        assert line["video_prompt"] == "waves, push-in"
        assert line["image_prompt"] == "Max waves at the park gate"
        assert line["characters"] == ["Max", "Dog"]

    def test_validate_script_defaults_optional_fields(self):
        s = validate_script(VALID_SCRIPT)
        line = s["scenes"][0]["lines"][0]
        assert line["video_prompt"] == ""
        assert line["image_prompt"] == ""
        assert line["characters"] == []

    def test_shots_from_script_merges_dialogue_into_one_shot(self):
        shots = shots_from_script(
            project_id=7,
            script=VALID_SCRIPT,
            models=DEFAULT_MODELS,
            tts_voice="alex",
            resolve_character=lambda name: None,
        )
        # 同 scene 连续两句合并为一个对白镜
        assert [s.order_index for s in shots] == [1]
        assert shots[0].project_id == 7
        assert [ln["en"] for ln in shots[0].dialogue] == ["Hi Kuku!", "Let's play together now!"]
        # characters 缺省 → 说话角色并集
        assert shots[0].ref_character_ids == [1, 3]
        assert shots[0].video_prompt == ""
        # 回退 prompt 只含场景，不含角色外形（外形由队列按模型能力注入）
        assert "At the park" in shots[0].image_prompt
        assert shots[0].asset_state(AssetKind.IMAGE) == AssetState.PENDING

    def test_shots_from_script_prefers_llm_image_prompt(self):
        script = {
            "scenes": [
                {
                    "setting": "park",
                    "lines": [
                        {
                            "character_id": 1,
                            "en": "Hi!",
                            "zh": "嗨",
                            "image_prompt": "wide shot of a sunny park gate, dog waving",
                        }
                    ],
                }
            ]
        }
        shots = shots_from_script(
            project_id=7,
            script=script,
            models=DEFAULT_MODELS,
            tts_voice="alex",
            resolve_character=lambda name: None,
        )
        assert shots[0].image_prompt == "wide shot of a sunny park gate, dog waving"

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
            models=DEFAULT_MODELS,
            tts_voice="alex",
            resolve_character=lambda name: {"max": 7}.get(name.lower()),
        )
        # Ghost 解析不到被忽略，Max 去重保序；说话角色 id 并入
        assert shots[0].ref_character_ids == [7, 1]
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

    def test_missing_compose_items_video_only(self):
        s = _shot()
        s.mark_running(AssetKind.IMAGE)
        s.mark_succeeded(AssetKind.IMAGE, path="p")
        items = missing_compose_items([s])
        kinds = {i["kind"] for i in items}
        assert kinds == {"video"}

    def test_stale_items_lists_staled_kinds(self):
        s = _shot()
        for kind in AssetKind:
            s.mark_running(kind)
            s.mark_succeeded(kind, path="p")
        s.apply_patch(image_prompt="new", dialogue=[{"character_id": 1, "en": "new", "zh": ""}])
        items = stale_items([s])
        assert {i["kind"] for i in items} == {"image", "video"}
        assert all(i["shot_order"] == s.order_index for i in items)


# ---------------- 对白镜（dialogue） ----------------


def _dline(cid: int | None, en: str, zh: str = "", **kw) -> dict:
    return {"character_id": cid, "en": en, "zh": zh, **kw}


def _dialogue_shot(dialogue: list[dict]) -> AvShot:
    return AvShot.create(
        project_id=1,
        order_index=1,
        ref_character_ids=[1, 2],
        dialogue=dialogue,
        image_prompt="two dogs in a sunny park",
        video_prompt="",
        models=DEFAULT_MODELS,
        tts_voice="alex",
    )


class TestDialogueValidation:
    def test_validate_dialogue_normalizes(self):
        out = validate_dialogue([{"character_id": None, "en": " Hi! ", "zh": " 嗨 "}])
        assert out == [{"character_id": None, "en": "Hi!", "zh": "嗨"}]

    def test_validate_dialogue_rejects_five_lines(self):
        with pytest.raises(ParamException):
            validate_dialogue([_dline(1, f"l{i}") for i in range(5)])

    def test_validate_dialogue_rejects_empty_en(self):
        with pytest.raises(ParamException):
            validate_dialogue([_dline(1, "  ")])

    def test_validate_dialogue_rejects_non_list(self):
        with pytest.raises(ParamException):
            validate_dialogue({"en": "hi"})

    def test_estimate_dialogue_duration_clamped(self):
        assert estimate_dialogue_duration([]) == 3.0
        assert estimate_dialogue_duration([_dline(1, "Hi!")]) == 3.0
        many = [_dline(1, " ".join(["word"] * 30)) for _ in range(2)]
        assert estimate_dialogue_duration(many) == 10.0
        mid = estimate_dialogue_duration([_dline(1, "one two three"), _dline(2, "four five six")])
        assert 3.0 < mid < 10.0


class TestGroupScript:
    def _script(self, *scenes):
        return validate_script({"scenes": list(scenes)})

    def test_merges_consecutive_lines_within_scene(self):
        script = self._script(
            {
                "setting": "park",
                "lines": [
                    _dline(1, "Hello Lily"),
                    _dline(2, "Hi Max"),
                    _dline(1, "Repeat after me: apple"),
                    _dline(2, "Apple! 苹果"),
                    _dline(1, "Great job"),
                ],
            }
        )
        groups = group_script_into_shots(script)
        assert [len(g["dialogue"]) for g in groups] == [4, 1]

    def test_duration_cap_splits_group(self):
        long_line = " ".join(["word"] * 8)  # 每句 ~3.6s
        script = self._script(
            {"setting": "park", "lines": [_dline(1, long_line), _dline(2, long_line),
                                          _dline(1, long_line), _dline(2, long_line)]}
        )
        groups = group_script_into_shots(script)
        assert [len(g["dialogue"]) for g in groups] == [2, 2]

    def test_scene_boundary_breaks_group(self):
        script = self._script(
            {"setting": "park", "lines": [_dline(1, "Hi")]},
            {"setting": "home", "lines": [_dline(2, "Hello")]},
        )
        groups = group_script_into_shots(script)
        assert len(groups) == 2

    def test_collects_prompts_names_and_speakers(self):
        script = self._script(
            {
                "setting": "park",
                "lines": [
                    _dline(1, "Hi", image_prompt="", characters=["Max"]),
                    _dline(2, "Hello", image_prompt="two dogs by the pond",
                           video_prompt="gentle push-in", characters=["Lily"]),
                ],
            }
        )
        g = group_script_into_shots(script)[0]
        assert g["image_prompt"] == "two dogs by the pond"
        assert g["video_prompt"] == "gentle push-in"
        assert g["character_names"] == ["Max", "Lily"]
        assert g["speaker_ids"] == [1, 2]

    def test_fallback_image_prompt_uses_setting(self):
        script = self._script({"setting": "At the park", "lines": [_dline(1, "Hi")]})
        g = group_script_into_shots(script)[0]
        assert "At the park" in g["image_prompt"]


class TestDialogueShot:
    def test_has_dialogue_property(self):
        s = _dialogue_shot([_dline(1, "a")])
        assert s.has_dialogue
        assert not _dialogue_shot([]).has_dialogue

    def test_create_estimates_duration_from_dialogue(self):
        s = _dialogue_shot([_dline(1, " ".join(["w"] * 10)), _dline(2, " ".join(["w"] * 10))])
        assert s.duration_estimate == estimate_dialogue_duration(s.dialogue)

    def test_apply_patch_dialogue_stales_video_only_and_recomputes(self):
        s = _dialogue_shot([_dline(1, "a")])
        for kind in (AssetKind.IMAGE, AssetKind.VIDEO):
            s.mark_running(kind)
            s.mark_succeeded(kind, path=f"p/{kind.value}")
        new = [_dline(1, "a much longer line indeed"), _dline(2, "reply here")]
        staled = s.apply_patch(dialogue=new)
        assert staled == [AssetKind.VIDEO]
        assert s.video_stale and not s.image_stale
        assert s.duration_estimate == estimate_dialogue_duration(new)

    def test_apply_patch_rejects_invalid_dialogue(self):
        s = _dialogue_shot([_dline(1, "a")])
        with pytest.raises(ParamException):
            s.apply_patch(dialogue=[_dline(1, "")])

    def test_apply_patch_rejects_legacy_fields(self):
        s = _dialogue_shot([_dline(1, "a")])
        with pytest.raises(ParamException):
            s.apply_patch(line_en="nope")


class TestAudioRetired:
    def test_project_status_ignores_audio(self):
        s = _dialogue_shot([_dline(1, "a")])
        for kind in (AssetKind.IMAGE, AssetKind.VIDEO):
            s.mark_running(kind)
            s.mark_succeeded(kind, path=f"p/{kind.value}")
        assert derive_project_status([s], queue_active=False) == "completed"

    def test_missing_compose_items_only_video(self):
        s = _dialogue_shot([_dline(1, "a")])
        s.mark_running(AssetKind.IMAGE)
        s.mark_succeeded(AssetKind.IMAGE, path="p/i")
        missing = missing_compose_items([s])
        assert missing == [{"shot_id": s.id, "shot_order": 1, "kind": "video"}]


class TestLegacyBackfill:
    def test_legacy_shot_to_dialogue_builds_single_line(self):
        assert legacy_shot_to_dialogue(3, "Hello", "你好") == [
            {"character_id": 3, "en": "Hello", "zh": "你好"}
        ]

    def test_legacy_shot_to_dialogue_empty_line_is_empty_list(self):
        assert legacy_shot_to_dialogue(None, "", "") == []
        assert legacy_shot_to_dialogue(None, "   ", "") == []
