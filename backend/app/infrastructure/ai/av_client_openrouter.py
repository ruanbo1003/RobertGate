"""ai-videos OpenRouter 生成客户端（t2i / i2v / tts / llm-json）。

接口形态（openrouter.ai/docs，2026-11-05 核实）：
- 文生图  POST {base}/images（aspect_ratio 9:16；参考图走 input_references，
          响应 data[0].b64_json，缺失回退 data[0].url 下载）
- 图生视频 POST {base}/videos（异步任务）→ GET {base}/videos/{id} 轮询
          → GET {base}/videos/{id}/content?index=0 下载 mp4
- TTS     POST {base}/chat/completions 流式（modalities audio，拼接
          choices[0].delta.audio.data 的 base64 分块）
- LLM     POST {base}/chat/completions（response_format=json_object）

错误约定与 SiliconFlow 版一致：401/402（及 429+credit/balance）→
ServerException(AV_UPSTREAM_QUOTA)，队列据此全局暂停；其余 → AV_UPSTREAM_FAILED。
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging

import httpx

from app.domain.errors import ServerException, codes

logger = logging.getLogger(__name__)

_QUOTA_STATUS = {401, 402}
_VIDEO_POLL_INTERVAL = 5.0
_VIDEO_POLL_TIMEOUT = 600.0
_DURATION_MIN, _DURATION_MAX = 2, 10

_SPEECH_SYSTEM = (
    "You are a text-to-speech engine. Read the user's text aloud verbatim, "
    "word for word. Do not add, omit, translate or comment on anything."
)


def _data_url(image: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(image).decode()


def _raise_upstream(resp: httpx.Response, what: str) -> None:
    body = resp.text[:300]
    logger.error("%s failed: status=%s body=%s", what, resp.status_code, body)
    if resp.status_code in _QUOTA_STATUS or (
        resp.status_code == 429
        and ("balance" in body.lower() or "credit" in body.lower())
    ):
        raise ServerException(codes.AV_UPSTREAM_QUOTA, "OpenRouter 余额不足或 Key 失效")
    raise ServerException(
        codes.AV_UPSTREAM_FAILED, f"{what} 上游失败 (HTTP {resp.status_code})"
    )


class OpenRouterAvClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
        poll_interval: float = _VIDEO_POLL_INTERVAL,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._transport = transport
        self._poll_interval = poll_interval

    def _http(self, timeout: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=timeout, transport=self._transport, follow_redirects=True
        )

    async def _request(
        self, method: str, url: str, what: str, timeout: float = 120.0, **kwargs
    ) -> httpx.Response:
        try:
            async with self._http(timeout) as client:
                resp = await client.request(method, url, headers=self._headers, **kwargs)
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what} 网络错误：{e}") from e
        if resp.status_code >= 400:
            _raise_upstream(resp, what)
        return resp

    # ---------------- t2i ----------------

    async def generate_image(
        self, prompt: str, model: str, reference_images: list[bytes] | None = None
    ) -> bytes:
        payload: dict = {
            "model": model,
            "prompt": prompt,
            "aspect_ratio": "9:16",
            "n": 1,
        }
        if reference_images:
            payload["input_references"] = [
                {"type": "image_url", "image_url": {"url": _data_url(img)}}
                for img in reference_images
            ]
        resp = await self._request(
            "POST", f"{self._base}/images", "文生图", json=payload
        )
        items = resp.json().get("data") or []
        item = items[0] if items else {}
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            dl = await self._request(
                "GET", item["url"], "文生图下载", timeout=300.0
            )
            return dl.content
        raise ServerException(codes.AV_UPSTREAM_FAILED, "文生图响应缺少图片数据")

    # ---------------- i2v ----------------

    async def generate_video(
        self, image: bytes, prompt: str, model: str, duration_seconds: int
    ) -> bytes:
        payload = {
            "model": model,
            "prompt": prompt,
            "frame_images": [
                {
                    "type": "image_url",
                    "image_url": {"url": _data_url(image)},
                    "frame_type": "first_frame",
                }
            ],
            "aspect_ratio": "9:16",
            "resolution": "720p",
            "duration": max(_DURATION_MIN, min(_DURATION_MAX, duration_seconds)),
        }
        submit = await self._request(
            "POST", f"{self._base}/videos", "图生视频提交", json=payload
        )
        job_id = submit.json().get("id")
        if not job_id:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "图生视频提交未返回任务 id")

        waited = 0.0
        while waited <= _VIDEO_POLL_TIMEOUT:
            await asyncio.sleep(self._poll_interval)
            waited += max(self._poll_interval, 1.0)
            status_resp = await self._request(
                "GET", f"{self._base}/videos/{job_id}", "图生视频查询", timeout=60.0
            )
            data = status_resp.json()
            status = str(data.get("status") or "").lower()
            if status in ("completed", "succeeded", "success"):
                content = await self._request(
                    "GET",
                    f"{self._base}/videos/{job_id}/content",
                    "图生视频下载",
                    timeout=300.0,
                    params={"index": 0},
                )
                return content.content
            if status in ("failed", "error", "cancelled"):
                reason = str(data.get("error") or data.get("reason") or "unknown")[:200]
                raise ServerException(
                    codes.AV_UPSTREAM_FAILED, f"图生视频失败：{reason}"
                )
        raise ServerException(codes.AV_UPSTREAM_FAILED, "图生视频超时（10 分钟）")

    # ---------------- tts ----------------

    async def generate_speech(self, text: str, model: str, voice: str) -> bytes:
        payload = {
            "model": model,
            "modalities": ["text", "audio"],
            "audio": {"voice": voice, "format": "mp3"},
            "stream": True,
            "messages": [
                {"role": "system", "content": _SPEECH_SYSTEM},
                {"role": "user", "content": text},
            ],
        }
        chunks: list[bytes] = []
        try:
            async with self._http(300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base}/chat/completions",
                    headers=self._headers,
                    json=payload,
                ) as resp:
                    if resp.status_code >= 400:
                        await resp.aread()
                        _raise_upstream(resp, "TTS")
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = event.get("choices") or []
                        delta = choices[0].get("delta") if choices else None
                        audio = (delta or {}).get("audio") or {}
                        if audio.get("data"):
                            chunks.append(base64.b64decode(audio["data"]))
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"TTS 网络错误：{e}") from e
        if not chunks:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "TTS 响应不含音频数据")
        return b"".join(chunks)

    # ---------------- llm ----------------

    async def generate_json(self, system: str, user: str, model: str) -> dict:
        resp = await self._request(
            "POST",
            f"{self._base}/chat/completions",
            "LLM",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
            },
        )
        try:
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"LLM 返回非法 JSON：{e}") from e
