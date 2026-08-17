"""下载生图结果的图片字节：T2IGenerator 的 FetchImage 实现，跑真实网络 I/O。"""

from __future__ import annotations

import httpx


async def fetch_image_bytes(url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type", "image/png")
