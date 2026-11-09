"""KieVideoClient 单测：httpx.MockTransport 验证上传/createTask/轮询/下载。"""

from __future__ import annotations

import json

import httpx
import pytest

from app.domain.errors import ServerException, codes
from app.infrastructure.ai.av_client_kie import KieVideoClient

BASE = "https://api.kie.test/api/v1"
UPLOAD_BASE = "https://upload.kie.test/api"
MP4 = b"\x00\x00mp4-fake"


def make_client(handler, **kw) -> KieVideoClient:
    return KieVideoClient(
        api_key="k",
        base=BASE,
        upload_base=UPLOAD_BASE,
        transport=httpx.MockTransport(handler),
        poll_interval=0.0,
        **kw,
    )


def _ok_handler(calls: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "success",
                        "resultJson": json.dumps({"resultUrls": ["https://files.test/out.mp4"]}),
                    }
                },
            )
        if request.url.path.endswith("/out.mp4"):
            return httpx.Response(200, content=MP4)
        raise AssertionError(f"unexpected request: {request.url}")

    return handler


async def test_generate_dialogue_video_happy_path():
    calls: list[str] = []
    out = await make_client(_ok_handler(calls)).generate_dialogue_video(
        b"img-bytes", "two dogs talking", duration_seconds=8
    )
    assert out == MP4
    assert any(p.endswith("/file-stream-upload") for p in calls)
    assert any(p.endswith("/jobs/createTask") for p in calls)
    assert any(p.endswith("/jobs/recordInfo") for p in calls)


async def test_create_task_sends_expected_payload():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "success",
                        "resultJson": {"resultUrls": ["https://files.test/out.mp4"]},
                    }
                },
            )
        return httpx.Response(200, content=MP4)

    await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert captured["model"] == "gemini-omni-video"
    assert captured["input"]["prompt"] == "p"
    assert captured["input"]["image_urls"] == ["https://files.test/x.png"]
    assert captured["input"]["aspect_ratio"] == "9:16"
    assert captured["input"]["resolution"] == "720p"


@pytest.mark.parametrize("requested,expected", [(7, "8"), (11, "10"), (4, "4"), (6, "6")])
async def test_duration_snaps_to_ladder(requested, expected):
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "success",
                        "resultJson": {"resultUrls": ["https://files.test/out.mp4"]},
                    }
                },
            )
        return httpx.Response(200, content=MP4)

    await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=requested)
    assert captured["input"]["duration"] == expected


async def test_success_with_empty_result_urls_raises_upstream_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200, json={"data": {"state": "success", "resultJson": {"resultUrls": []}}}
            )
        raise AssertionError("should not download")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_job_fail_state_raises_upstream_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, json={"data": {"state": "fail", "failMsg": "boom"}})
        raise AssertionError("should not download")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_timeout_raises_upstream_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, json={"data": {"state": "waiting"}})
        raise AssertionError("should not download")

    client = make_client(handler, poll_timeout=0.0)
    with pytest.raises(ServerException) as e:
        await client.generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_download_error_is_upstream_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "state": "success",
                        "resultJson": {"resultUrls": ["https://files.test/out.mp4"]},
                    }
                },
            )
        if request.url.path.endswith("/out.mp4"):
            return httpx.Response(404, text="not found")
        raise AssertionError(f"unexpected: {request.url}")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


@pytest.mark.parametrize("status", [401, 402, 429])
async def test_upload_quota_status_raises_av_upstream_quota(status):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(status, text="no credits")
        raise AssertionError("should not reach createTask")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_QUOTA


async def test_create_task_quota_status_raises_av_upstream_quota():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(402, text="insufficient credits")
        raise AssertionError("should not reach recordInfo")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_QUOTA
