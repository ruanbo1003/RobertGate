"""kie.ai 对白镜（音视同出）生成客户端。

接口形态（docs.kie.ai，2026-11-09 核实）：
- 上传首帧图 POST {upload_base}/file-stream-upload（multipart）→ data.downloadUrl
- 创建任务  POST {base}/jobs/createTask → data.taskId
- 轮询状态  GET  {base}/jobs/recordInfo?taskId= → data.state
            success → data.resultJson（字符串则 json.loads）.resultUrls[0]
- 下载产物  GET resultUrls[0]（第三方 CDN，不带 Authorization）

错误约定（2026-11-13 真机探测修正）：kie 的 HTTP 状态码恒为 200，错误码在
body 的 code 字段里——判错必须读 body。401/402，以及消息里带 balance/credit
字样的 429 → ServerException(AV_UPSTREAM_QUOTA)（队列据此全局暂停）；其余
（限流 429、422、5xx、success 无 resultUrls、job state=fail、超时、下载失败）
→ ServerException(AV_UPSTREAM_FAILED)。另：recordInfo 的 param 字段嵌套转义
缺层导致整体可能是非法 JSON，解析走 _parse_body 容错（剥 param 再读）。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx

from app.domain.errors import ServerException, codes

logger = logging.getLogger(__name__)

_QUOTA_STATUS = {401, 402}
_DURATION_LADDER = (4, 6, 8, 10)
# 轮询期瞬时上游错误（限流/5xx）的连续容忍次数：任务已计费，不能一撞就丢
_POLL_TRANSIENT_LIMIT = 3
# recordInfo 的 param 字段转义缺层会毒化整个 JSON（形状随 input 内容变化，
# 无法整体修复）：按字段定向提取，拼回最小合法结构
_CODE_RE = re.compile(r'"code"\s*:\s*(\d+)')
_STATE_RE = re.compile(r'"state"\s*:\s*"([a-zA-Z_]+)"')
_STR_FIELD_RES = {
    name: re.compile(rf'"{name}"\s*:\s*"((?:[^"\\]|\\.)*)"')
    for name in ("resultJson", "failMsg", "msg")
}


def _extract_fields(text: str) -> dict:
    """非法 JSON 的兜底解析：定向抓 code/state/resultJson/failMsg/msg，
    与 param 的具体形状无关。"""
    body: dict = {}
    data: dict = {}
    if m := _CODE_RE.search(text):
        body["code"] = int(m.group(1))
    if m := _STATE_RE.search(text):
        data["state"] = m.group(1)
    for name, pattern in _STR_FIELD_RES.items():
        if m := pattern.search(text):
            # 还原字符串字面量的转义（\" -> " 等）
            try:
                value = json.loads('"' + m.group(1) + '"')
            except json.JSONDecodeError:
                value = m.group(1)
            if name == "msg":
                body[name] = value
            else:
                data[name] = value
    if data:
        body["data"] = data
    return body


def _is_quota(code: int, text: str) -> bool:
    """401/402 恒为配额错误；429 仅当消息带 balance/credit（余额类）才算。"""
    if code in _QUOTA_STATUS:
        return True
    low = text.lower()
    return code == 429 and ("balance" in low or "credit" in low)


def _snap_duration(seconds: int) -> str:
    for step in _DURATION_LADDER:
        if seconds <= step:
            return str(step)
    return str(_DURATION_LADDER[-1])


def _raise_upstream(resp: httpx.Response, what: str) -> None:
    body = resp.text[:300]
    logger.error("kie %s failed: status=%s body=%s", what, resp.status_code, body)
    if _is_quota(resp.status_code, body):
        raise ServerException(codes.AV_UPSTREAM_QUOTA, "kie.ai 余额不足或 Key 失效")
    raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what} 上游失败 (HTTP {resp.status_code})")


def _parse_body(resp: httpx.Response, what: str) -> dict:
    """kie 响应统一出口：HTTP 层判错 + 容错解析 + body code 判错，返回整个 body。"""
    if resp.status_code >= 400:
        _raise_upstream(resp, what)
    try:
        body = resp.json()
    except ValueError as e:
        body = _extract_fields(resp.text)
        if not body:
            logger.error("kie %s invalid json: %s", what, resp.text[:300])
            raise ServerException(
                codes.AV_UPSTREAM_FAILED, f"{what} 响应非法 JSON"
            ) from e
        logger.warning("kie %s 响应非法 JSON，已定向提取关键字段", what)
    code = body.get("code")
    if isinstance(code, int) and code != 200:
        msg = str(body.get("msg") or "")[:300]
        logger.error("kie %s failed: body code=%s msg=%s", what, code, msg)
        if _is_quota(code, msg):
            raise ServerException(codes.AV_UPSTREAM_QUOTA, "kie.ai 余额不足或 Key 失效")
        raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what} 上游失败 ({code}: {msg[:120]})")
    return body


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
        url = ((_parse_body(resp, "图片上传").get("data") or {}).get("downloadUrl"))
        if not url:
            raise ServerException(codes.AV_UPSTREAM_FAILED, "图片上传响应缺少 downloadUrl")
        return url

    async def _create_task(self, image_url: str, prompt: str, duration_seconds: int) -> str:
        return await self._create_task_for(
            self._model,
            {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": _snap_duration(duration_seconds),
                "aspect_ratio": "9:16",
                "resolution": "720p",
            },
            "创建任务",
        )

    async def _create_task_for(self, model: str, task_input: dict, what: str) -> str:
        """通用 createTask：任意模型 + input，返回 taskId。"""
        payload = {"model": model, "input": task_input}
        try:
            async with self._http(60.0) as client:
                resp = await client.post(
                    f"{self._base}/jobs/createTask", headers=self._headers, json=payload
                )
        except httpx.HTTPError as e:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what}网络错误：{e}") from e
        task_id = ((_parse_body(resp, what).get("data") or {}).get("taskId"))
        if not task_id:
            raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what}响应缺少 taskId")
        return task_id

    async def _poll_result_url(self, task_id: str) -> str:
        return await self._poll_result(task_id, self._poll_interval, "对白镜生成")

    async def _poll_result(self, task_id: str, interval: float, what: str) -> str:
        """通用轮询：success → resultJson.resultUrls[0]；fail → 抛错；
        未知 state 继续轮，超时消息带最后一次 state 便于排障。"""
        waited = 0.0
        last_state = ""
        transient = 0
        while waited <= self._poll_timeout:
            await asyncio.sleep(interval)
            waited += max(interval, 1.0)
            # 任务已在上游跑且已计费：查询期的瞬时错误（限流/5xx/网络抖动）
            # 有限容忍，连续超限才放弃；配额错误（401/402/余额类 429）立即抛
            try:
                try:
                    async with self._http(60.0) as client:
                        resp = await client.get(
                            f"{self._base}/jobs/recordInfo",
                            headers=self._headers,
                            params={"taskId": task_id},
                        )
                except httpx.HTTPError as e:
                    raise ServerException(
                        codes.AV_UPSTREAM_FAILED, f"{what}查询网络错误：{e}"
                    ) from e
                body = _parse_body(resp, f"{what}查询")
            except ServerException as e:
                if e.code == codes.AV_UPSTREAM_QUOTA:
                    raise
                transient += 1
                if transient >= _POLL_TRANSIENT_LIMIT:
                    raise
                logger.warning("%s查询瞬时失败（%d/%d），继续轮询：%s",
                               what, transient, _POLL_TRANSIENT_LIMIT, e.message)
                continue
            transient = 0
            data = body.get("data") or {}
            state = str(data.get("state") or "").lower()
            last_state = state or last_state
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
                raise ServerException(codes.AV_UPSTREAM_FAILED, f"{what}失败：{reason}")
        raise ServerException(
            codes.AV_UPSTREAM_FAILED, f"{what}超时（最后状态 {last_state or 'unknown'}）"
        )

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
