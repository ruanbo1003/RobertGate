"""ai-videos 可选模型清单（kie.ai 主通道，Robert 2026-11-13 拍板迁移）。

静态配置：GET /ai-videos/models 直接返回本清单，前端各处模型下拉据此渲染。
模型 id 为 kie.ai 裸 id（单通道，不带渠道前缀）；dialogue_video 段是唯一
跨渠道段，维持 `渠道:模型` tag 格式（kie 主 + OpenRouter 兜底，见
av_dialogue_router.py）。

真机验证（2026-11-13，见 specs/2026-11-13-kie-migration-design.md 探测结果）：
- llm：gemini-3-8-flash-openai 走 OpenAI 兼容 /v1/chat/completions，
  json_object 生效（-openai 后缀 = 同步端点；不带后缀的同名 id 属 jobs 侧）。
  注意 /v1/models 的列表不可信：gpt-5.5 在列却 422 "not supported"，
  任何新条目入表前必须真机调通（勿只看列表）。
- t2i：nano-banana-2 多参考图（input.image_urls 数组）+ 9:16 验证通过，
  单图 10s；seedream 5.5 省钱档出图 + 9:16 验证通过（1584×2816），
  参考图未验，标 none。
- i2v：bytedance/seedance-2-fast durations 4/5/6/8 实测合法（3 → 422），
  10s+ 档位因余额不足未探明，待补。
- tts：死链路不迁（生成端入口全被拦，见 spec"TTS 不在范围内"），原样保留
  仅为 API 契约兼容。
"""

from __future__ import annotations

AV_MODELS: dict[str, list[dict]] = {
    "llm": [
        {
            "id": "gemini-3-8-flash-openai",
            "name": "Gemini 3.8 Flash",
            "default": True,
        },
    ],
    "t2i": [
        {
            "id": "nano-banana-2",
            "name": "Nano Banana 2",
            "default": True,
            "reference": "multi",
        },
        {
            "id": "seedream/5-5-text-to-image",
            "name": "Seedream 5.5（省钱档）",
            "reference": "none",
        },
    ],
    "i2v": [
        {
            "id": "bytedance/seedance-2-fast",
            "name": "Seedance 2 Fast",
            "default": True,
            "durations": [4, 5, 6, 8],
        },
    ],
    "tts": [
        # tts 链路已退役（对白镜音视同出替代），本段仅保 API 契约，不可生成
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


def is_known_model(model_type: str, model_id: str) -> bool:
    """模型 id 是否在当前注册表内（活配置读取回退的判据）。"""
    return any(m["id"] == model_id for m in AV_MODELS.get(model_type, []))


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
