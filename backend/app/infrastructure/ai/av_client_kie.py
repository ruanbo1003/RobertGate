"""kie.ai 对白镜（音视同出）生成客户端。

接口形态（docs.kie.ai，2026-11-09 核实）：
- 上传首帧图 POST {upload_base}/file-stream-upload（multipart）→ data.downloadUrl
- 创建任务  POST {base}/jobs/createTask → data.taskId
- 轮询状态  GET  {base}/jobs/recordInfo?taskId= → data.state
            success → data.resultJson（字符串则 json.loads）.resultUrls[0]
- 下载产物  GET resultUrls[0]（第三方 CDN，不带 Authorization）

错误约定：401/402/429 → ServerException(AV_UPSTREAM_QUOTA)；
其余失败（上游 4xx/5xx、success 无 resultUrls、job state=fail、超时、下载失败）→
ServerException(AV_UPSTREAM_FAILED)。
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx

from app.domain.errors import ServerException, codes

logger = logging.getLogger(__name__)

_QUOTA_STATUS = {401, 402, 429}
_DURATION_LADDER = (4, 6, 8, 10)


def _snap_duration(seconds: int) -> str:
    for step in _DURATION_LADDER:
        if seconds <= step:
            return str(step)
    return str(_DURATION_LADDER[-1])


def _raise_upstream(resp: httpx.Response, what: str) -> None:
    body = resp.text[:300]
    logger.error("kie %s failed: status=%s body=%s", what, resp.status_code, body)
    if resp.status_code in _QUOTA_STATUS:
        raise ServerException(codes.AV_UPSTREAM_QUOTA, "kie.ai 余额不足或 Key 失效")
    raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what} 上游失败 (HTTP {resp.status_code})")


class KieVideoClient:
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-omni-video",
        base: str = "https://api.kie.ai/api/v1",
        upload_base: str = "https://kieai.redpandaai.co/api",
        poll_interval: float = 10.0,
        poll_timeout: float = 900.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base = base.rstrip("/")
        self._upload_base = upload_base.rstrip("/")
        self._poll_interval = poll_interval
        self._poll_timeout = poll_timeout
        self._transport = transport
        self._headers = {"Authorization": f"Bearer {api_key}"}

    def _http(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout, transport=self._transport, follow_redirects=True
        )

    async def _upload_image(self, image: bytes) -> str:
        try:
            async with self._http(60.0) as client:
                resp = await client.post(
                    f"{self._upload_base}/file-stream-upload",
                    headers=self._headers,
                    files={"file": ("shot.png", image, "image/png")},
                    data={"uploadPath": "av-dialogue", "fileName": "shot.png"},
                )
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"图片上传网络错误：{e}") from e
        if resp.status_code >= 400:
            _raise_upstream(resp, "图片上传")
        url = ((resp.json().get("data") or {}).get("downloadUrl"))
        if not url:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "图片上传响应缺少 downloadUrl")
        return url

    async def _create_task(self, image_url: str, prompt: str, duration_seconds: int) -> str:
        payload = {
            "model": self._model,
            "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": _snap_duration(duration_seconds),
                "aspect_ratio": "9:16",
                "resolution": "720p",
            },
        }
        try:
            async with self._http(60.0) as client:
                resp = await client.post(
                    f"{self._base}/jobs/createTask", headers=self._headers, json=payload
                )
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"创建任务网络错误：{e}") from e
        if resp.status_code >= 400:
            _raise_upstream(resp, "创建任务")
        task_id = ((resp.json().get("data") or {}).get("taskId"))
        if not task_id:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "创建任务响应缺少 taskId")
        return task_id

    async def _poll_result_url(self, task_id: str) -> str:
        waited = 0.0
        while waited <= self._poll_timeout:
            await asyncio.sleep(self._poll_interval)
            waited += max(self._poll_interval, 1.0)
            try:
                async with self._http(60.0) as client:
                    resp = await client.get(
                        f"{self._base}/jobs/recordInfo",
                        headers=self._headers,
                        params={"taskId": task_id},
                    )
            except httpx.HTTPError as e:
                raise ServerException(codes.AV_UPSTREAM_FAILED, f"查询任务网络错误：{e}") from e
            if resp.status_code >= 400:
                _raise_upstream(resp, "查询任务")
            data = resp.json().get("data") or {}
            state = str(data.get("state") or "").lower()
            if state == "success":
                result_json = data.get("resultJson")
                if isinstance(result_json, str):
                    try:
                        result_json = json.loads(result_json or "{}")
                    except json.JSONDecodeError as e:
                        raise ServerException(
                            codes.AV_UPSTREAM_FAILED, f"任务成功但 resultJson 解析失败：{e}"
                        ) from e
                urls = (result_json or {}).get("resultUrls") or []
                if not urls:
                    raise ServerException(codes.AV_UPSTREAM_FAILED, "任务成功但未返回产物")
                return urls[0]
            if state in ("fail", "failed", "error"):
                reason = str(data.get("failMsg") or data.get("error") or "unknown")[:200]
                raise ServerException(codes.AV_UPSTREAM_FAILED, f"对白镜生成失败：{reason}")
        raise ServerException(codes.AV_UPSTREAM_FAILED, "对白镜生成超时")

    async def _download(self, url: str) -> bytes:
        try:
            async with self._http(300.0) as client:
                resp = await client.get(url)
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"产物下载网络错误：{e}") from e
        if resp.status_code >= 400:
            raise ServerException(
                codes.AV_UPSTREAM_FAILED, f"产物下载失败 (HTTP {resp.status_code})"
            )
        return resp.content

    async def generate_dialogue_video(
        self, image: bytes, prompt: str, duration_seconds: int
    ) -> bytes:
        image_url = await self._upload_image(image)
        task_id = await self._create_task(image_url, prompt, duration_seconds)
        result_url = await self._poll_result_url(task_id)
        return await self._download(result_url)
