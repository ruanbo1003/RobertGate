"""模型注册表（kie.ai 主通道）单测。"""

from app.infrastructure.data.av_models import (
    AV_MODELS,
    default_model,
    default_voice,
    is_known_model,
    reference_mode,
    snap_duration,
)


def test_registry_segments_and_shape():
    assert set(AV_MODELS) == {"llm", "t2i", "i2v", "tts", "dialogue_video"}
    for key, entries in AV_MODELS.items():
        assert entries


def test_default_models_are_kie_ids():
    assert default_model("llm") == "gemini-3-8-flash-openai"
    assert default_model("t2i") == "nano-banana-2"
    assert default_model("i2v") == "bytedance/seedance-2-fast"
    assert default_model("tts") == "openai/gpt-audio"  # tts 不迁，原样保留


def test_dialogue_video_segment_keeps_channel_tags():
    ids = {m["id"] for m in AV_MODELS["dialogue_video"]}
    assert "kie:gemini-omni-video" in ids
    assert "openrouter:bytedance/seedance-2.0-fast" in ids


def test_reference_mode_resolves_for_new_default_t2i():
    # Review Focus 1：匹配落空会静默返回 "none"，角色跨镜变脸
    assert reference_mode(default_model("t2i")) == "multi"
    for m in AV_MODELS["t2i"]:
        assert m.get("reference") in ("multi", "none")
    assert reference_mode("unknown/x") == "none"


def test_snap_duration_resolves_for_new_default_i2v():
    # Review Focus 1：匹配落空会静默掉进 max(2, min(10, s)) 兜底分支。
    # 档位 [4,5,6,8] 为真机验证值（10s+ 因余额不足未探，见 spec 真机探测结果 #4）
    model = default_model("i2v")
    assert snap_duration(model, 3) == 4
    assert snap_duration(model, 5) == 5
    assert snap_duration(model, 7) == 6  # 平手取小
    assert snap_duration(model, 99) == 8
    assert snap_duration("unknown/x", 99) == 10
    assert snap_duration("unknown/x", 1) == 2


def test_is_known_model_rejects_retired_openrouter_id():
    assert is_known_model("t2i", "google/gemini-3.1-flash-image") is False
    assert is_known_model("llm", "google/gemini-3.8-flash") is False
    assert is_known_model("i2v", "bytedance/seedance-2.0-fast") is False


def test_is_known_model_accepts_current_entries():
    for seg in ("llm", "t2i", "i2v", "tts"):
        for m in AV_MODELS[seg]:
            assert is_known_model(seg, m["id"]) is True


def test_default_voice_matches_default_tts_model():
    tts = next(m for m in AV_MODELS["tts"] if m.get("default"))
    assert default_voice() == tts["voices"][0]


def test_llm_segment_has_no_unverified_entries():
    # Final review I2：gpt-5.5 真机 422 "not supported"（/v1/models 列表不可信），
    # 假的下拉选项比没有选项更坏
    assert is_known_model("llm", "gpt-5.5") is False
