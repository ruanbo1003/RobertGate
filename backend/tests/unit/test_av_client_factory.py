"""av 客户端工厂（OpenRouter-only）与 Mock 行为单测。"""

from __future__ import annotations

import pytest

import app.infrastructure.ai.av_client as av_client_module
from app.infrastructure.ai.av_client import (
    AvClientWithDialogue,
    MockAvClient,
    get_av_client,
    set_av_client,
)
from app.infrastructure.ai.av_client_kie import KieVideoClient
from app.infrastructure.ai.av_client_openrouter import OpenRouterAvClient
from app.infrastructure.ai.av_dialogue_router import DialogueVideoRouter


@pytest.fixture(autouse=True)
def _reset_singleton():
    set_av_client(None)
    yield
    set_av_client(None)


def _patch_settings(monkeypatch, openrouter_key: str, kie_key: str = ""):
    class _S:
        OPENROUTER_API_KEY = openrouter_key
        OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
        AV_FFMPEG_BIN = "ffmpeg"
        AV_TTS_TEMPO = 1.0
        KIE_API_KEY = kie_key
        KIE_BASE_URL = "https://kie.test/api/v1"
        KIE_UPLOAD_BASE_URL = "https://upload.kie.test/api"
        AV_DIALOGUE_MODEL = "gemini-omni-video"
        AV_DIALOGUE_FALLBACK_MODEL = "bytedance/seedance-2.0-fast"

    monkeypatch.setattr(av_client_module, "_load_settings", lambda: _S())


def test_factory_wraps_openrouter_with_dialogue_router(monkeypatch):
    _patch_settings(monkeypatch, "sk-or-xxx")
    client = get_av_client()
    assert isinstance(client, AvClientWithDialogue)
    assert isinstance(client._base, OpenRouterAvClient)
    assert isinstance(client._router, DialogueVideoRouter)
    # 没配 KIE_API_KEY：primary 缺席，router 退化为 fallback-only
    assert client._router._primary is None
    assert client._router._fallback_tag == "openrouter:bytedance/seedance-2.0-fast"


def test_factory_wires_kie_primary_when_key_set(monkeypatch):
    _patch_settings(monkeypatch, "sk-or-xxx", kie_key="kie-key")
    client = get_av_client()
    assert isinstance(client._router._primary, KieVideoClient)
    assert client._router._primary_tag == "kie:gemini-omni-video"


def test_factory_returns_mock_without_key(monkeypatch):
    _patch_settings(monkeypatch, "")
    assert isinstance(get_av_client(), MockAvClient)


async def test_av_client_with_dialogue_delegates_to_base_and_router():
    class FakeBase:
        def __init__(self):
            self.calls = []

        async def generate_image(self, prompt, model, reference_images=None):
            self.calls.append(("image", prompt, model, reference_images))
            return b"img"

        async def generate_video(self, image, prompt, model, duration_seconds=5, generate_audio=False):
            self.calls.append(("video", image, prompt, model, duration_seconds, generate_audio))
            return b"vid"

        async def generate_speech(self, text, model, voice):
            self.calls.append(("speech", text, model, voice))
            return b"aud"

        async def generate_json(self, system, user, model):
            self.calls.append(("json", system, user, model))
            return {"ok": True}

    class FakeRouter:
        def __init__(self):
            self.calls = []

        async def generate_dialogue_video(self, image, prompt, duration_seconds):
            self.calls.append((image, prompt, duration_seconds))
            return b"dlg", "kie:gemini-omni-video"

    base, router = FakeBase(), FakeRouter()
    client = AvClientWithDialogue(base, router)

    assert await client.generate_image("p", "m") == b"img"
    assert await client.generate_video(b"i", "p", "m", 7, True) == b"vid"
    assert await client.generate_speech("t", "m", "v") == b"aud"
    assert await client.generate_json("s", "u", "m") == {"ok": True}
    video, tag = await client.generate_dialogue_video(b"i", "p", 8)
    assert (video, tag) == (b"dlg", "kie:gemini-omni-video")
    assert base.calls == [
        ("image", "p", "m", None),
        ("video", b"i", "p", "m", 7, True),
        ("speech", "t", "m", "v"),
        ("json", "s", "u", "m"),
    ]
    assert router.calls == [(b"i", "p", 8)]


async def test_mock_script_lines_carry_video_prompt_and_characters():
    raw = await MockAvClient().generate_json("s", "u", "m")
    line = raw["scenes"][0]["lines"][0]
    assert line["video_prompt"]
    assert isinstance(line["characters"], list) and line["characters"]


async def test_mock_generate_video_accepts_duration():
    out = await MockAvClient().generate_video(b"img", "p", "m", duration_seconds=4)
    assert out.startswith(b"\x00\x00\x00\x18ftyp")
