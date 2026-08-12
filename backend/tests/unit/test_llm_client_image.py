"""Tests for LLMClient.generate_image (CogView-3-Flash / OpenAI 兼容协议)."""

from __future__ import annotations

import pytest

from app.service import llm_client as llm_mod
from app.service.llm_client import LLMClient


class _FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json


class _FakeAsyncClient:
    """Async context manager stand-in for httpx.AsyncClient used by generate_image."""

    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[tuple[str, dict, dict]] = []

    def __call__(self, *args, **kwargs):  # httpx.AsyncClient(timeout=...) construction
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict, headers: dict) -> _FakeResponse:
        self.calls.append((url, json, headers))
        return self._response


def _client() -> LLMClient:
    return LLMClient(
        api_key="sk-test",
        model="glm-4.6",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        image_model="cogview-3-flash",
        image_size="1024x1024",
    )


@pytest.mark.asyncio
async def test_generate_image_success(monkeypatch):
    fake = _FakeAsyncClient(
        _FakeResponse(200, {"data": [{"url": "https://cdn.example.com/x.png"}]})
    )
    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", fake)

    url = await _client().generate_image("a cute cat")

    assert url == "https://cdn.example.com/x.png"
    assert len(fake.calls) == 1
    endpoint, body, headers = fake.calls[0]
    assert endpoint == "https://open.bigmodel.cn/api/paas/v4/images/generations"
    assert body == {
        "model": "cogview-3-flash",
        "prompt": "a cute cat",
        "size": "1024x1024",
    }
    assert headers["Authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
async def test_generate_image_http_error(monkeypatch):
    fake = _FakeAsyncClient(_FakeResponse(429, text="rate limited"))
    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", fake)

    with pytest.raises(RuntimeError) as exc:
        await _client().generate_image("prompt")
    assert "429" in str(exc.value)


@pytest.mark.asyncio
async def test_generate_image_missing_data(monkeypatch):
    fake = _FakeAsyncClient(_FakeResponse(200, {"data": []}))
    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", fake)

    with pytest.raises(RuntimeError):
        await _client().generate_image("prompt")


@pytest.mark.asyncio
async def test_generate_image_missing_url(monkeypatch):
    fake = _FakeAsyncClient(_FakeResponse(200, {"data": [{}]}))
    monkeypatch.setattr(llm_mod.httpx, "AsyncClient", fake)

    with pytest.raises(RuntimeError):
        await _client().generate_image("prompt")
