"""模型注册表（多 provider）单测。"""

from app.infrastructure.data.av_models import (
    AV_MODELS,
    default_model,
    default_voice,
    model_provider,
    reference_mode,
)


def test_every_entry_has_provider():
    for entries in AV_MODELS.values():
        for m in entries:
            assert m["provider"] in ("openrouter", "siliconflow")


def test_defaults_are_openrouter():
    for t in ("llm", "t2i", "i2v", "tts"):
        assert model_provider(default_model(t)) == "openrouter"


def test_reference_mode():
    assert reference_mode("google/gemini-3.1-flash-image") == "multi"
    assert reference_mode("Kwai-Kolors/Kolors") == "single"
    assert reference_mode("Qwen/Qwen-Image") == "none"
    assert reference_mode("unknown/x") == "none"


def test_model_provider_unknown_falls_back_to_siliconflow():
    assert model_provider("unknown/x") == "siliconflow"


def test_default_voice_matches_default_tts_model():
    tts = next(m for m in AV_MODELS["tts"] if m.get("default"))
    assert default_voice() == tts["voices"][0]
