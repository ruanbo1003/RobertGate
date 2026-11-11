"""对白镜 prompt 构建与时长取档纯函数单测。"""

from __future__ import annotations

from app.application.services.av_dialogue import build_dialogue_prompt, snap_dialogue_duration


def test_build_dialogue_prompt_two_speakers():
    prompt = build_dialogue_prompt(
        scene_hint="two dogs in a sunny park",
        speakers=[
            {"id": 1, "name": "Max", "voice_desc": "warm friendly"},
            {"id": 2, "name": "Lily", "voice_desc": "high cheerful"},
        ],
        dialogue=[
            {"character_id": 1, "en": "Hello Lily! Repeat after me: apple.", "zh": ""},
            {"character_id": 2, "en": "Apple! 苹果!", "zh": ""},
        ],
    )
    assert "children's storybook cartoon" in prompt
    assert "two dogs in a sunny park" in prompt
    assert "Max has a warm friendly voice" in prompt
    assert "Lily has a high cheerful voice" in prompt
    assert 'Max says: "Hello Lily! Repeat after me: apple."' in prompt
    assert 'Then Lily says: "Apple! 苹果!"' in prompt
    assert "mouths" in prompt.lower()
    assert "no background music" in prompt.lower()
    assert "clear speech" in prompt.lower()


def test_build_dialogue_prompt_first_line_has_no_then():
    prompt = build_dialogue_prompt(
        scene_hint="park",
        speakers=[{"id": 1, "name": "Max", "voice_desc": ""}],
        dialogue=[{"character_id": 1, "en": "Hi!", "zh": ""}],
    )
    assert 'Max says: "Hi!"' in prompt
    assert "Then Max says" not in prompt
    # 空 voice_desc 回退 clear friendly
    assert "Max has a clear friendly voice" in prompt


def test_build_dialogue_prompt_narrator_for_missing_speaker():
    prompt = build_dialogue_prompt(
        scene_hint="park",
        speakers=[{"id": 1, "name": "Max", "voice_desc": "warm"}],
        dialogue=[
            {"character_id": 1, "en": "Hi!", "zh": ""},
            {"character_id": None, "en": "And they played all day.", "zh": ""},
            {"character_id": 99, "en": "Unknown speaker line.", "zh": ""},
        ],
    )
    assert 'Then the narrator says: "And they played all day."' in prompt
    assert 'Then the narrator says: "Unknown speaker line."' in prompt


def test_snap_dialogue_duration_rounds_up_to_ladder():
    assert snap_dialogue_duration(7.2, (4, 6, 8, 10)) == 8
    assert snap_dialogue_duration(3.0, (4, 6, 8, 10)) == 4
    assert snap_dialogue_duration(4.0, (4, 6, 8, 10)) == 4


def test_snap_dialogue_duration_clamps_to_max():
    assert snap_dialogue_duration(15.0, (4, 6, 8, 10)) == 10
