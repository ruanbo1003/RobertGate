"""ai-videos 可选模型清单（OpenRouter 单 provider，Robert 2026-11-05 拍板）。

静态配置：GET /ai-videos/models 直接返回本清单，前端各处模型下拉据此渲染。
t2i 条目带 reference 参考图能力档：
- "multi" 多参考图（OpenRouter /images 的 input_references，角色一致性最佳）
- "none"  纯文生图（角色一致性由队列拼外形描述兜底）

全部条目已于 2026-11-05 真机验证（每模型一次最小调用）：
- t2i 三款均出图；gemini-3.1-flash-image 带 2 张参考图验证通过；
  gemini-3-pro-image 在低余额账号会 402（单图预扣成本高），功能本身正常。
- i2v 四款均出片（duration 按 durations 档位吸附）。
- tts 两款均出声（流式 pcm16 → ffmpeg 转 mp3）。
- llm：原计划的 google/gemini-3-flash 不存在，换为最新稳定版 gemini-3.8-flash。
"""

from __future__ import annotations

AV_MODELS: dict[str, list[dict]] = {
    "llm": [
        {"id": "google/gemini-3.8-flash", "name": "Gemini 3.8 Flash", "default": True},
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
        # durations：OpenRouter 真机 400 报错给出的允许档位（2026-11-05 实测）
        {
            "id": "bytedance/seedance-2.0-fast",
            "name": "Seedance 2.0 Fast",
            "default": True,
            "durations": list(range(4, 16)),
        },
        {"id": "alibaba/wan-3.0", "name": "Wan 3.0", "durations": list(range(2, 16))},
        {
            "id": "kwaivgi/kling-v3.0-std",
            "name": "Kling 3.0 Std",
            "durations": list(range(3, 16)),
        },
        {"id": "google/veo-3.1-fast", "name": "Veo 3.1 Fast", "durations": [4, 6, 8]},
    ],
    "tts": [
        # chat/completions 流式音频输出；alloy 已真机验证
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
    # 对白镜（音视同出）：唯一跨渠道段，仅展示用——路由固定为 kie 主+OpenRouter 兜底
    # （见 av_dialogue_router.py），id 即 shot.video_model 落库的渠道:模型 tag。
    "dialogue_video": [
        {"id": "kie:gemini-omni-video", "name": "Gemini Omni (kie.ai)", "default": True},
        {
            "id": "openrouter:bytedance/seedance-2.0-fast",
            "name": "Seedance 2.0 Fast（兜底）",
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


def snap_duration(model_id: str, seconds: int) -> int:
    """把时长吸附到模型允许档位（最近者，平手取小）；未知模型夹到 [2,10]。"""
    for m in AV_MODELS["i2v"]:
        if m["id"] == model_id and m.get("durations"):
            return min(m["durations"], key=lambda d: (abs(d - seconds), d))
    return max(2, min(10, seconds))
