"""av 客户端工厂（OpenRouter-only）与 Mock 行为单测。"""

from __future__ import annotations

import pytest

import app.infrastructure.ai.av_client as av_client_module
from app.infrastructure.ai.av_client import MockAvClient, get_av_client, set_av_client
from app.infrastructure.ai.av_client_openrouter import OpenRouterAvClient


@pytest.fixture(autouse=True)
def _reset_singleton():
    set_av_client(None)
    yield
    set_av_client(None)


def _patch_settings(monkeypatch, openrouter_key: str):
    class _S:
        OPENROUTER_API_KEY = openrouter_key
        OPENROUTER_BASE_URL = "https://openrouter.test/api/v1"
        AV_FFMPEG_BIN = "ffmpeg"
        AV_TTS_TEMPO = 1.0

    monkeypatch.setattr(av_client_module, "_load_settings", lambda: _S())


def test_factory_returns_openrouter_when_key_set(monkeypatch):
    _patch_settings(monkeypatch, "sk-or-xxx")
    assert isinstance(get_av_client(), OpenRouterAvClient)


def test_factory_returns_mock_without_key(monkeypatch):
    _patch_settings(monkeypatch, "")
    assert isinstance(get_av_client(), MockAvClient)


async def test_mock_script_lines_carry_video_prompt_and_characters():
    raw = await MockAvClient().generate_json("s", "u", "m")
    line = raw["scenes"][0]["lines"][0]
    assert line["video_prompt"]
    assert isinstance(line["characters"], list) and line["characters"]


async def test_mock_generate_video_accepts_duration():
    out = await MockAvClient().generate_video(b"img", "p", "m", duration_seconds=4)
    assert out.startswith(b"\x00\x00\x00\x18ftyp")
