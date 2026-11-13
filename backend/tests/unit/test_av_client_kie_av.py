"""KieAvClient 单测：t2i / i2v / 退役 tts（httpx.MockTransport 打桩）。"""

from __future__ import annotations

import json

import httpx
import pytest

from app.domain.errors import ServerException, codes
from app.infrastructure.ai.av_client_kie_av import KieAvClient

BASE = "https://api.kie.test/api/v1"
UPLOAD_BASE = "https://upload.kie.test/api"
CHAT_BASE = "https://api.kie.test/v1"
PNG = b"\x89PNG-fake"
MP4 = b"\x00\x00mp4-fake"


def make_client(handler, **kw) -> KieAvClient:
    return KieAvClient(
        api_key="k",
        base=BASE,
        upload_base=UPLOAD_BASE,
        chat_base=CHAT_BASE,
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        image_poll_interval=0.0,
        **kw,
    )


def _jobs_handler(captured: dict, result_url: str, content: bytes):
    uploads = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            uploads["n"] += 1
            captured["uploads"] = uploads["n"]
            return httpx.Response(
                200, json={"code": 200, "data": {"downloadUrl": f"https://files.test/u{uploads['n']}.png"}}
            )
        if request.url.path.endswith("/jobs/createTask"):
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {"state": "success", "resultJson": json.dumps({"resultUrls": [result_url]})},
                },
            )
        if request.url == result_url:
            return httpx.Response(200, content=content)
        raise AssertionError(f"unexpected: {request.url}")

    return handler


async def test_generate_image_passes_multiple_reference_images():
    captured: dict = {}
    out = await make_client(_jobs_handler(captured, "https://files.test/out.png", PNG)).generate_image(
        "a dog and a cat", "nano-banana-2", reference_images=[b"ref1", b"ref2"]
    )
    assert out == PNG
    assert captured["uploads"] == 2
    assert captured["model"] == "nano-banana-2"
    assert captured["input"]["image_urls"] == ["https://files.test/u1.png", "https://files.test/u2.png"]
    assert captured["input"]["aspect_ratio"] == "9:16"
    assert captured["input"]["prompt"] == "a dog and a cat"


async def test_generate_image_without_refs_omits_image_urls():
    captured: dict = {}
    await make_client(_jobs_handler(captured, "https://files.test/out.png", PNG)).generate_image(
        "a park", "nano-banana-2"
    )
    assert "image_urls" not in captured["input"]
    assert captured.get("uploads") is None


async def test_generate_image_upload_failure_raises_not_silently_drops():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"code": 500, "msg": "boom", "data": None})
        raise AssertionError("createTask 不应被调用：参考图丢失 = 角色变脸")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_image("p", "nano-banana-2", reference_images=[b"r"])
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_unknown_poll_state_keeps_polling_and_timeout_reports_last_state():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, json={"code": 200, "data": {"state": "weird_state"}})
        raise AssertionError(f"unexpected: {request.url}")

    client = make_client(handler, poll_timeout=0.0)
    with pytest.raises(ServerException) as e:
        await client.generate_image("p", "nano-banana-2")
    assert e.value.code == codes.AV_UPSTREAM_FAILED
    assert "weird_state" in e.value.message


async def test_generate_video_snaps_duration_and_sends_audio_flag():
    captured: dict = {}
    out = await make_client(_jobs_handler(captured, "https://files.test/out.mp4", MP4)).generate_video(
        b"first-frame", "dog runs", "bytedance/seedance-2-fast", duration_seconds=7, generate_audio=True
    )
    assert out == MP4
    assert captured["input"]["duration"] == "6"  # 7 → 档位 [4,5,6,8] 平手取小
    assert captured["input"]["image_urls"] == ["https://files.test/u1.png"]
    assert captured["input"]["generate_audio"] is True
    assert captured["input"]["resolution"] == "720p"


async def test_generate_speech_is_retired():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("tts 已退役，不应发任何请求")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_speech("hi", "openai/gpt-audio", "alloy")
    assert e.value.code == codes.AV_UPSTREAM_FAILED
    assert "退役" in e.value.message


async def test_quota_body_code_propagates():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 402, "msg": "Credits insufficient", "data": None})
        raise AssertionError("unreachable")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_image("p", "nano-banana-2")
    assert e.value.code == codes.AV_UPSTREAM_QUOTA


async def test_image_poll_interval_defaults_short():
    c = KieAvClient(api_key="k", chat_base=CHAT_BASE)
    assert c._image_poll_interval == 2.5
