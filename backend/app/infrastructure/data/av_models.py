"""ai-videos 可选模型清单（OpenRouter 单 provider，Robert 2026-11-05 拍板）。

静态配置：GET /ai-videos/models 直接返回本清单，前端各处模型下拉据此渲染。
t2i 条目带 reference 参考图能力档：
- "multi" 多参考图（OpenRouter /images 的 input_references，角色一致性最佳）
- "none"  纯文生图（角色一致性由队列拼外形描述兜底）

slug 待 Task 10 真机核实（GET /models 与 ?output_modalities=video），
验证不过的替换为同系可用款并在此注释说明。
"""

from __future__ import annotations

AV_MODELS: dict[str, list[dict]] = {
    "llm": [
        {"id": "google/gemini-3-flash", "name": "Gemini 3 Flash", "default": True},
        {"id": "deepseek/deepseek-v3.2", "name": "DeepSeek V3.2"},
    ],
    "t2i": [
        {
            "id": "google/gemini-3.1-flash-image",
            "name": "Gemini 3.1 Flash Image",
            "default": True,
            "reference": "multi",
        },
        {
            "id": "google/gemini-3-pro-image",
            "name": "Gemini 3 Pro Image",
            "reference": "multi",
        },
        {
            "id": "google/gemini-nano-banana-2.1",
            "name": "Nano Banana 2.1",
            "reference": "multi",
        },
    ],
    "i2v": [
        {"id": "bytedance/seedance-2.0-fast", "name": "Seedance 2.0 Fast", "default": True},
        {"id": "alibaba/wan-3.0", "name": "Wan 3.0"},
        {"id": "kwaivgi/kling-v3.0-std", "name": "Kling 3.0 Std"},
        {"id": "google/veo-3.1-fast", "name": "Veo 3.1 Fast"},
    ],
    "tts": [
        # chat/completions 流式音频输出；voices 待 Task 10 实测
        {
            "id": "openai/gpt-audio",
            "name": "GPT Audio",
            "default": True,
            "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        },
        {
            "id": "openai/gpt-audio-mini",
            "name": "GPT Audio Mini",
            "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        },
    ],
}


def default_model(model_type: str) -> str:
    models = AV_MODELS[model_type]
    for m in models:
        if m.get("default"):
            return m["id"]
    return models[0]["id"]


def reference_mode(model_id: str) -> str:
    """t2i 模型的参考图能力档：multi / none（非 t2i 或未知为 none）。"""
    for m in AV_MODELS["t2i"]:
        if m["id"] == model_id:
            return m.get("reference", "none")
    return "none"


def default_voice() -> str:
    tts = next((m for m in AV_MODELS["tts"] if m.get("default")), AV_MODELS["tts"][0])
    voices = tts.get("voices") or ["alloy"]
    return voices[0]
