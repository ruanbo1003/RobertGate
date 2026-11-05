"""OpenRouterAvClient 单测：httpx.MockTransport 验证请求组装与响应解析。"""

from __future__ import annotations

import base64
import json

import httpx
import pytest

from app.domain.errors import ServerException, codes
from app.infrastructure.ai.av_client_openrouter import OpenRouterAvClient

BASE = "https://openrouter.test/api/v1"
PNG = b"\x89PNG-fake"
MP4 = b"\x00\x00mp4-fake"


def make_client(handler) -> OpenRouterAvClient:
    return OpenRouterAvClient(
        api_key="k",
        base_url=BASE,
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
    )


# ---------------- images ----------------


async def test_generate_image_sends_aspect_ratio_and_references():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        captured["path"] = request.url.path
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(PNG).decode()}]}
        )

    out = await make_client(handler).generate_image(
        "a dog", "google/gemini-3.1-flash-image", reference_images=[b"img1", b"img2"]
    )
    assert out == PNG
    assert captured["path"].endswith("/images")
    assert captured["aspect_ratio"] == "9:16"
    assert captured["n"] == 1
    refs = captured["input_references"]
    assert len(refs) == 2
    assert refs[0]["image_url"]["url"].startswith("data:image/png;base64,")


async def test_generate_image_without_references_omits_field():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200, json={"data": [{"b64_json": base64.b64encode(PNG).decode()}]}
        )

    await make_client(handler).generate_image("a dog", "m")
    assert "input_references" not in captured


async def test_generate_image_falls_back_to_url():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images"):
            return httpx.Response(200, json={"data": [{"url": "https://files.test/x.png"}]})
        # 产物下载发往第三方 CDN，绝不能带 OpenRouter 的 Authorization 头
        assert "authorization" not in {k.lower() for k in request.headers}
        return httpx.Response(200, content=PNG)

    assert await make_client(handler).generate_image("p", "m") == PNG


async def test_image_download_error_is_not_quota():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/images"):
            return httpx.Response(200, json={"data": [{"url": "https://files.test/x.png"}]})
        return httpx.Response(402, content=b"cdn payment thing")

    with pytest.raises(ServerException) as ei:
        await make_client(handler).generate_image("p", "m")
    # CDN 的 402 不是 OpenRouter 配额错误，不能触发队列全局暂停
    assert ei.value.code == codes.AV_UPSTREAM_FAILED


async def test_generate_image_missing_b64_and_url_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{}]})

    with pytest.raises(ServerException) as ei:
        await make_client(handler).generate_image("p", "m")
    assert ei.value.code == codes.AV_UPSTREAM_FAILED


async def test_quota_status_maps_to_quota_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"error": "insufficient credits"})

    with pytest.raises(ServerException) as ei:
        await make_client(handler).generate_image("p", "m")
    assert ei.value.code == codes.AV_UPSTREAM_QUOTA


# ---------------- videos ----------------


async def test_generate_video_full_flow_and_duration_snap():
    captured: dict = {}
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "POST" and path.endswith("/videos"):
            captured.update(json.loads(request.content))
            return httpx.Response(202, json={"id": "job1", "status": "pending"})
        if path.endswith("/videos/job1") and "content" not in path:
            polls["n"] += 1
            status = "pending" if polls["n"] == 1 else "completed"
            return httpx.Response(200, json={"id": "job1", "status": status})
        if path.endswith("/videos/job1/content"):
            assert request.url.params["index"] == "0"
            return httpx.Response(200, content=MP4)
        raise AssertionError(f"unexpected {request.method} {path}")

    out = await make_client(handler).generate_video(
        b"frame", "dog runs", "bytedance/seedance-2.0-fast", duration_seconds=99
    )
    assert out == MP4
    assert polls["n"] == 2
    assert captured["duration"] == 15  # snap 到 seedance 允许档位上限
    assert captured["aspect_ratio"] == "9:16"
    assert captured["resolution"] == "720p"
    frame = captured["frame_images"][0]
    assert frame["frame_type"] == "first_frame"
    assert frame["image_url"]["url"].startswith("data:image/png;base64,")


async def test_generate_video_failed_status_raises_with_reason():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(202, json={"id": "j", "status": "pending"})
        return httpx.Response(200, json={"id": "j", "status": "failed", "error": "nsfw blocked"})

    with pytest.raises(ServerException) as ei:
        await make_client(handler).generate_video(b"f", "p", "m", duration_seconds=1)
    assert ei.value.code == codes.AV_UPSTREAM_FAILED
    assert "nsfw blocked" in ei.value.message


# ---------------- speech ----------------


def _sse(chunks: list[dict]) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


async def test_generate_speech_concatenates_pcm_chunks_and_transcodes(monkeypatch):
    import app.infrastructure.ai.av_client_openrouter as mod

    async def fake_transcode(pcm: bytes, ffmpeg_bin: str = "ffmpeg") -> bytes:
        return b"MP3:" + pcm

    monkeypatch.setattr(mod, "_pcm16_to_mp3", fake_transcode)
    captured: dict = {}
    a, b = base64.b64encode(b"pcm-a").decode(), base64.b64encode(b"pcm-b").decode()

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        body = _sse(
            [
                {"choices": [{"delta": {"audio": {"data": a}}}]},
                {"choices": [{"delta": {"content": "ignored text"}}]},
                {"choices": [{"delta": {"audio": {"data": b}}}]},
            ]
        )
        return httpx.Response(200, content=body)

    out = await make_client(handler).generate_speech("Hi there", "openai/gpt-audio", "alloy")
    assert out == b"MP3:pcm-apcm-b"
    assert captured["modalities"] == ["text", "audio"]
    # OpenAI 流式音频仅支持 pcm16，客户端收完后 ffmpeg 转 mp3
    assert captured["audio"] == {"voice": "alloy", "format": "pcm16"}
    assert captured["stream"] is True


async def test_generate_speech_no_audio_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=_sse([{"choices": [{"delta": {"content": "text only"}}]}])
        )

    with pytest.raises(ServerException) as ei:
        await make_client(handler).generate_speech("Hi", "m", "alloy")
    assert ei.value.code == codes.AV_UPSTREAM_FAILED


# ---------------- json ----------------


async def test_generate_json_parses_content():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["response_format"] == {"type": "json_object"}
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"scenes": []}'}}]},
        )

    assert await make_client(handler).generate_json("s", "u", "m") == {"scenes": []}


async def test_generate_speech_uses_configured_ffmpeg_bin(monkeypatch):
    import app.infrastructure.ai.av_client_openrouter as mod

    seen: dict = {}

    async def fake_transcode(pcm: bytes, ffmpeg_bin: str = "ffmpeg") -> bytes:
        seen["bin"] = ffmpeg_bin
        return b"mp3"

    monkeypatch.setattr(mod, "_pcm16_to_mp3", fake_transcode)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=_sse(
                [{"choices": [{"delta": {"audio": {"data": base64.b64encode(b"p").decode()}}}]}]
            ),
        )

    client = OpenRouterAvClient(
        api_key="k", base_url=BASE,
        transport=httpx.MockTransport(handler), poll_interval=0.0,
        ffmpeg_bin="/opt/ffmpeg-full/bin/ffmpeg",
    )
    assert await client.generate_speech("Hi", "m", "alloy") == b"mp3"
    assert seen["bin"] == "/opt/ffmpeg-full/bin/ffmpeg"
