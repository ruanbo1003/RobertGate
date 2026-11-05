"""模型注册表（OpenRouter-only）单测。"""

from app.infrastructure.data.av_models import (
    AV_MODELS,
    default_model,
    default_voice,
    reference_mode,
)


def test_registry_is_openrouter_only_and_typed():
    assert set(AV_MODELS) == {"llm", "t2i", "i2v", "tts"}
    for entries in AV_MODELS.values():
        assert entries
        for m in entries:
            assert "provider" not in m


def test_default_models():
    assert default_model("llm") == "google/gemini-3.8-flash"
    assert default_model("t2i") == "google/gemini-3.1-flash-image"
    assert default_model("i2v") == "bytedance/seedance-2.0-fast"
    assert default_model("tts") == "openai/gpt-audio"


def test_reference_mode_multi_or_none_only():
    for m in AV_MODELS["t2i"]:
        assert m.get("reference") in ("multi", "none")
    assert reference_mode("google/gemini-3.1-flash-image") == "multi"
    assert reference_mode("unknown/x") == "none"


def test_default_voice_matches_default_tts_model():
    tts = next(m for m in AV_MODELS["tts"] if m.get("default"))
    assert default_voice() == tts["voices"][0]


def test_snap_duration_per_model():
    from app.infrastructure.data.av_models import snap_duration

    assert snap_duration("bytedance/seedance-2.0-fast", 3) == 4
    assert snap_duration("bytedance/seedance-2.0-fast", 99) == 15
    assert snap_duration("kwaivgi/kling-v3.0-std", 2) == 3
    assert snap_duration("google/veo-3.1-fast", 5) == 4  # 平手取小
    assert snap_duration("google/veo-3.1-fast", 7) == 6
    assert snap_duration("alibaba/wan-3.0", 2) == 2
    assert snap_duration("unknown/x", 99) == 10
    assert snap_duration("unknown/x", 1) == 2
