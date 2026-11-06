"""ai-videos 客户端装配：OpenRouter 实现（见 av_client_openrouter.py）+ Mock + 工厂。

Robert 2026-11-05 拍板：模型只用 OpenRouter。原 SiliconFlowAvClient 已删除
（需要时从 git 历史恢复）。未配 OPENROUTER_API_KEY 时整体落到 MockAvClient，
保证无 Key 环境全链路可走通（开发/联调语义不变）。
"""

from __future__ import annotations

import asyncio
import base64

from app.infrastructure.ai.av_client_openrouter import OpenRouterAvClient

# 1x1 透明 PNG，mock 产物占位
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


class MockAvClient:
    """无 Key 环境的假实现：立即返回占位产物，保证全链路可走通。"""

    async def generate_image(
        self, prompt: str, model: str, reference_images: list[bytes] | None = None
    ) -> bytes:
        await asyncio.sleep(0.05)
        return _TINY_PNG

    async def generate_video(
        self, image: bytes, prompt: str, model: str, duration_seconds: int = 5
    ) -> bytes:
        await asyncio.sleep(0.05)
        return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64  # 伪 mp4 头

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        await asyncio.sleep(0.05)
        return b"ID3" + b"\x00" * 64  # 伪 mp3 头

    async def generate_json(self, system: str, user: str, model: str) -> dict:
        await asyncio.sleep(0.05)
        return {
            "scenes": [
                {
                    "setting": "At the park",
                    "lines": [
                        {
                            "character_id": 1,
                            "en": "What a nice day!",
                            "zh": "天气真好！",
                            "image_prompt": "wide shot of a sunny park, blue sky",
                            "video_prompt": "the character waves happily, camera static, sunny mood",
                            "characters": ["dog"],
                        },
                        {
                            "character_id": 1,
                            "en": "Let's play together!",
                            "zh": "一起玩吧！",
                            "image_prompt": "medium shot on the park lawn, a red ball nearby",
                            "video_prompt": "the character jumps with joy, slow push-in",
                            "characters": ["dog"],
                        },
                    ],
                }
            ]
        }


_av_client = None


def _load_settings():
    """间接层：测试可 monkeypatch。"""
    from app.config import get_settings

    return get_settings()


def get_av_client():
    """全局单例：配置了 OPENROUTER_API_KEY 用 OpenRouter，否则用 Mock。"""
    global _av_client
    if _av_client is not None:
        return _av_client
    settings = _load_settings()
    if settings.OPENROUTER_API_KEY:
        _av_client = OpenRouterAvClient(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            ffmpeg_bin=settings.AV_FFMPEG_BIN,
        )
    else:
        _av_client = MockAvClient()
    return _av_client


def set_av_client(client) -> None:
    """测试/联调替换；传 None 重置单例。"""
    global _av_client
    _av_client = client
