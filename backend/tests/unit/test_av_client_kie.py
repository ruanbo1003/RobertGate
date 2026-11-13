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


async def test_success_with_malformed_result_json_raises_upstream_failed():
    # 终审发现：kie 偶发返回脏 resultJson 字符串时 json.loads 抛的是
    # JSONDecodeError（非 ServerException），router 捕获不到 → 不触发
    # 兜底降级，直接把整镜标失败。kie.ai 口碑里这类"偶发故障"是真实存在的。
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(
                200, json={"data": {"state": "success", "resultJson": "{not valid json"}}
            )
        raise AssertionError("should not download")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


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


# ---- kie 实际形态：HTTP 恒 200、错误码在 body code（2026-11-13 真机探测）----


def _body_code_handler(code: int, msg: str):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": code, "msg": msg, "data": None})
        raise AssertionError("should not reach recordInfo")

    return handler


@pytest.mark.parametrize("code,msg", [(401, "Unauthorized"), (402, "Credits insufficient : top up")])
async def test_http200_body_quota_code_raises_av_upstream_quota(code, msg):
    with pytest.raises(ServerException) as e:
        await make_client(_body_code_handler(code, msg)).generate_dialogue_video(
            b"img", "p", duration_seconds=5
        )
    assert e.value.code == codes.AV_UPSTREAM_QUOTA


async def test_http200_body_422_raises_av_upstream_failed():
    with pytest.raises(ServerException) as e:
        await make_client(_body_code_handler(422, "Invalid duration")).generate_dialogue_video(
            b"img", "p", duration_seconds=5
        )
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_http200_body_429_rate_limit_is_plain_failure():
    # 纯限流 429（无 balance/credit 字样）→ 单产物失败，不得全局暂停整条产线
    with pytest.raises(ServerException) as e:
        await make_client(_body_code_handler(429, "Too many requests")).generate_dialogue_video(
            b"img", "p", duration_seconds=5
        )
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_http200_body_429_with_credit_keyword_is_quota():
    with pytest.raises(ServerException) as e:
        await make_client(
            _body_code_handler(429, "credit limit reached")
        ).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_QUOTA


async def test_http429_status_without_keyword_is_plain_failure():
    # 旧判据按 HTTP 429 一律 QUOTA；拆分后无关键字 → FAILED
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(429, text="rate limited, slow down")
        raise AssertionError("unreachable")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED


async def test_record_info_with_broken_param_field_still_parses():
    # 真机实测：recordInfo 的 param 字段嵌套转义缺层 → 整体非法 JSON，
    # resp.json() 直接抛 JSONDecodeError；解析必须容错（剥掉 param 再读）
    broken = (
        '{"code":200,"msg":"success","data":{"taskId":"t1","state":"success",'
        '"param":"{\\"input\\":\\"{\\\\"aspect_ratio\\\\":\\\\"9:16\\\\"}\\"}",'
        '"resultJson":"{\\"resultUrls\\":[\\"https://files.test/out.mp4\\"]}"}}'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, content=broken.encode(), headers={"content-type": "application/json"})
        if request.url.path.endswith("/out.mp4"):
            return httpx.Response(200, content=MP4)
        raise AssertionError(f"unexpected: {request.url}")

    out = await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert out == MP4


async def test_record_info_real_broken_body_from_production_parses():
    # Final review I1：真机抓到的 recordInfo 原文（param 多字段、转义缺层），
    # 合成串测不出的形状——定向提取必须扛住它
    from pathlib import Path

    raw = (Path(__file__).parent / "data" / "kie_record_info_broken_real.json").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, content=raw, headers={"content-type": "application/json"})
        if "aiquickdraw.com" in str(request.url):
            return httpx.Response(200, content=MP4)
        raise AssertionError(f"unexpected: {request.url}")

    out = await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert out == MP4


async def test_poll_tolerates_transient_rate_limit_then_succeeds():
    # Final review I4：轮询期撞限流 429 不得终结已计费任务，有限容忍后继续
    polls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            polls["n"] += 1
            if polls["n"] <= 2:
                return httpx.Response(200, json={"code": 429, "msg": "Too many requests"})
            return httpx.Response(
                200,
                json={"code": 200, "data": {"state": "success",
                      "resultJson": json.dumps({"resultUrls": ["https://files.test/out.mp4"]})}},
            )
        if request.url.path.endswith("/out.mp4"):
            return httpx.Response(200, content=MP4)
        raise AssertionError(f"unexpected: {request.url}")

    out = await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert out == MP4
    assert polls["n"] == 3


async def test_poll_quota_error_still_raises_immediately():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            calls["n"] += 1
            return httpx.Response(200, json={"code": 402, "msg": "Credits insufficient"})
        raise AssertionError(f"unexpected: {request.url}")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_QUOTA
    assert calls["n"] == 1  # 配额错误不重试


async def test_poll_persistent_transient_errors_eventually_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/file-stream-upload"):
            return httpx.Response(200, json={"data": {"downloadUrl": "https://files.test/x.png"}})
        if request.url.path.endswith("/jobs/createTask"):
            return httpx.Response(200, json={"code": 200, "data": {"taskId": "t1"}})
        if request.url.path.endswith("/jobs/recordInfo"):
            return httpx.Response(200, json={"code": 429, "msg": "Too many requests"})
        raise AssertionError(f"unexpected: {request.url}")

    with pytest.raises(ServerException) as e:
        await make_client(handler).generate_dialogue_video(b"img", "p", duration_seconds=5)
    assert e.value.code == codes.AV_UPSTREAM_FAILED
