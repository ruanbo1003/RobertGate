"""ai-videos 可选模型清单（多 provider：OpenRouter / SiliconFlow）。

静态配置：GET /ai-videos/models 直接返回本清单，前端各处模型下拉据此渲染。
每条带 provider（客户端按此路由到对应 base_url/Key/接口格式）；t2i 条目带
reference 参考图能力档：
- "multi"  多参考图（OpenRouter /images 的 input_references）
- "single" 单参考图（SiliconFlow Kolors 的 image 参数）
- "none"   纯文生图（角色一致性由队列拼外形描述兜底）

OpenRouter slug 均经 2026-11-05 真机核实（见各条注释，Task 10 复核）。
已排除：Qwen-Image-Edit 系（强制要求参考图，角色首图会 400）、
OpenMOSS-Team/MOSS-Image（不支持 720x1280 档位）。
"""

from __future__ import annotations

AV_MODELS: dict[str, list[dict]] = {
    "llm": [
        # 待 Task 10 验证 slug
        {
            "id": "google/gemini-3-flash",
            "name": "Gemini 3 Flash",
            "provider": "openrouter",
            "default": True,
        },
        {
            "id": "deepseek/deepseek-v3.2",
            "name": "DeepSeek V3.2",
            "provider": "openrouter",
        },
        {
            "id": "deepseek-ai/DeepSeek-V3",
            "name": "DeepSeek-V3 (SF)",
            "provider": "siliconflow",
        },
        {
            "id": "Qwen/Qwen2.5-72B-Instruct",
            "name": "Qwen2.5-72B (SF)",
            "provider": "siliconflow",
        },
    ],
    "t2i": [
        # Gemini 图像系：多参考图，角色一致性最佳。待 Task 10 验证 slug
        {
            "id": "google/gemini-3.1-flash-image",
            "name": "Gemini 3.1 Flash Image",
            "provider": "openrouter",
            "default": True,
            "reference": "multi",
        },
        {
            "id": "google/gemini-3-pro-image",
            "name": "Gemini 3 Pro Image",
            "provider": "openrouter",
            "reference": "multi",
        },
        {
            "id": "google/gemini-nano-banana-2.1",
            "name": "Nano Banana 2.1",
            "provider": "openrouter",
            "reference": "multi",
        },
        {
            "id": "Kwai-Kolors/Kolors",
            "name": "Kolors (SF)",
            "provider": "siliconflow",
            "reference": "single",
        },
        # 以下三个为纯文生图；均已真机验证支持 720x1280（2026-11-04）
        {
            "id": "Qwen/Qwen-Image",
            "name": "Qwen-Image (SF)",
            "provider": "siliconflow",
            "reference": "none",
        },
        {
            "id": "Tongyi-MAI/Z-Image-Turbo",
            "name": "Z-Image Turbo (SF)",
            "provider": "siliconflow",
            "reference": "none",
        },
        {
            "id": "Tongyi-MAI/Z-Image",
            "name": "Z-Image (SF)",
            "provider": "siliconflow",
            "reference": "none",
        },
    ],
    "i2v": [
        # OpenRouter /videos 异步任务接口。待 Task 10 验证 slug/档位
        {
            "id": "bytedance/seedance-2.0-fast",
            "name": "Seedance 2.0 Fast",
            "provider": "openrouter",
            "default": True,
        },
        {
            "id": "alibaba/wan-3.0",
            "name": "Wan 3.0",
            "provider": "openrouter",
        },
        {
            "id": "kwaivgi/kling-v3.0-std",
            "name": "Kling 3.0 Std",
            "provider": "openrouter",
        },
        {
            "id": "google/veo-3.1-fast",
            "name": "Veo 3.1 Fast",
            "provider": "openrouter",
        },
        {
            "id": "Wan-AI/Wan2.2-I2V-A14B",
            "name": "Wan2.2 I2V (SF)",
            "provider": "siliconflow",
        },
        {
            "id": "Wan-AI/Wan2.1-I2V-14B-720P",
            "name": "Wan2.1 I2V 720P (SF)",
            "provider": "siliconflow",
        },
    ],
    "tts": [
        # chat/completions 流式音频输出；voices 待 Task 10 实测
        {
            "id": "openai/gpt-audio",
            "name": "GPT Audio",
            "provider": "openrouter",
            "default": True,
            "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        },
        {
            "id": "openai/gpt-audio-mini",
            "name": "GPT Audio Mini",
            "provider": "openrouter",
            "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        },
        {
            "id": "FunAudioLLM/CosyVoice2-0.5B",
            "name": "CosyVoice2 (SF)",
            "provider": "siliconflow",
            "voices": ["alex", "anna", "benjamin", "bella"],
        },
    ],
}


def default_model(model_type: str) -> str:
    models = AV_MODELS[model_type]
    for m in models:
        if m.get("default"):
            return m["id"]
    return models[0]["id"]


def model_provider(model_id: str) -> str:
    """全类型查找模型所属 provider；未知模型兜底 siliconflow（历史数据兼容）。"""
    for entries in AV_MODELS.values():
        for m in entries:
            if m["id"] == model_id:
                return m["provider"]
    return "siliconflow"


def reference_mode(model_id: str) -> str:
    """t2i 模型的参考图能力档：multi / single / none（非 t2i 或未知为 none）。"""
    for m in AV_MODELS["t2i"]:
        if m["id"] == model_id:
            return m.get("reference", "none")
    return "none"


def default_voice() -> str:
    tts = next((m for m in AV_MODELS["tts"] if m.get("default")), AV_MODELS["tts"][0])
    voices = tts.get("voices") or ["alloy"]
    return voices[0]
