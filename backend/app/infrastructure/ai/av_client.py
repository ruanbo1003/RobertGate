"""ai-videos 客户端装配：kie.ai 主通道（av_client_kie_av.py）+ Mock + 工厂。

Robert 2026-11-13 拍板迁移 kie.ai（OpenRouter 账号被限闭源三家，见
specs/2026-11-13-kie-migration-design.md）。装配规则：
- 有 KIE_API_KEY：四线（llm/t2i/i2v/tts*）走 KieAvClient；对白镜 router
  primary 走 KieVideoClient，兜底仅在同时配了 OPENROUTER_API_KEY 时存在
  （OpenRouterAvClient 只服务这一处，四线不再经过它）。
- 无 KIE_API_KEY：整体 MockAvClient，保证无 Key 环境全链路可走通。
*tts 已退役，KieAvClient.generate_speech 直接抛错（链路入口在 service 层已被拦）。
"""

from __future__ import annotations

import asyncio
import base64

from app.infrastructure.ai.av_client_kie import KieVideoClient
from app.infrastructure.ai.av_client_kie_av import KieAvClient
from app.infrastructure.ai.av_client_openrouter import OpenRouterAvClient
from app.infrastructure.ai.av_dialogue_router import DialogueVideoRouter

_FALLBACK_DURATION_LADDER = (4, 6, 8, 10)

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
        self,
        image: bytes,
        prompt: str,
        model: str,
        duration_seconds: int = 5,
        generate_audio: bool = False,
    ) -> bytes:
        await asyncio.sleep(0.05)
        return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64  # 伪 mp4 头

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        await asyncio.sleep(0.05)
        return b"ID3" + b"\x00" * 64  # 伪 mp3 头

    async def generate_dialogue_video(
        self, image: bytes, prompt: str, duration_seconds: int
    ) -> tuple[bytes, str]:
        await asyncio.sleep(0.05)
        return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64, "mock:gemini-omni-video"

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


class AvClientWithDialogue:
    """组合基础 AvGenClient 实现 + DialogueVideoRouter，补上 generate_dialogue_video。

    其余四个方法原样委托给 base；dialogue 走 router（kie 主 + openrouter 兜底）。
    """

    def __init__(self, base, router: DialogueVideoRouter) -> None:
        self._base = base
        self._router = router

    async def generate_image(
        self, prompt: str, model: str, reference_images: list[bytes] | None = None
    ) -> bytes:
        return await self._base.generate_image(prompt, model, reference_images)

    async def generate_video(
        self,
        image: bytes,
        prompt: str,
        model: str,
        duration_seconds: int = 5,
        generate_audio: bool = False,
    ) -> bytes:
        return await self._base.generate_video(
            image, prompt, model, duration_seconds, generate_audio
        )

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        return await self._base.generate_speech(text, model, voice)

    async def generate_json(self, system: str, user: str, model: str) -> dict:
        return await self._base.generate_json(system, user, model)

    async def generate_dialogue_video(
        self, image: bytes, prompt: str, duration_seconds: int
    ) -> tuple[bytes, str]:
        return await self._router.generate_dialogue_video(image, prompt, duration_seconds)


_av_client = None


def _load_settings():
    """间接层：测试可 monkeypatch。"""
    from app.config import get_settings

    return get_settings()


def get_av_client():
    """全局单例：配置了 KIE_API_KEY 用 kie.ai（+ 对白镜路由），否则用 Mock。"""
    global _av_client
    if _av_client is not None:
        return _av_client
    settings = _load_settings()
    if settings.KIE_API_KEY:
        base = KieAvClient(
            api_key=settings.KIE_API_KEY,
            base=settings.KIE_BASE_URL,
            upload_base=settings.KIE_UPLOAD_BASE_URL,
            chat_base=settings.KIE_CHAT_BASE_URL,
        )
        primary = KieVideoClient(
            api_key=settings.KIE_API_KEY,
            model=settings.AV_DIALOGUE_MODEL,
            base=settings.KIE_BASE_URL,
            upload_base=settings.KIE_UPLOAD_BASE_URL,
        )
        fallback_video = None
        if settings.OPENROUTER_API_KEY:
            openrouter = OpenRouterAvClient(
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                ffmpeg_bin=settings.AV_FFMPEG_BIN,
                tts_tempo=settings.AV_TTS_TEMPO,
            )

            async def fallback_video(image: bytes, prompt: str, duration_seconds: int) -> bytes:
                return await openrouter.generate_video(
                    image,
                    prompt,
                    settings.AV_DIALOGUE_FALLBACK_MODEL,
                    duration_seconds,
                    generate_audio=True,
                )

        router = DialogueVideoRouter(
            primary=primary,
            fallback_video=fallback_video,
            primary_tag=f"kie:{settings.AV_DIALOGUE_MODEL}",
            fallback_tag=f"openrouter:{settings.AV_DIALOGUE_FALLBACK_MODEL}",
            fallback_ladder=_FALLBACK_DURATION_LADDER,
        )
        _av_client = AvClientWithDialogue(base, router)
    else:
        _av_client = MockAvClient()
    return _av_client


def set_av_client(client) -> None:
    """测试/联调替换；传 None 重置单例。"""
    global _av_client
    _av_client = client
