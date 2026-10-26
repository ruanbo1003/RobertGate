"""本地手工验证 CogView-3-Flash 文生图，并把结果保存到 scripts/images/。

运行方式（在 backend/ 下）：
    ENV=local uv run python scripts/test_t2i_cogview.py
    ENV=local uv run python scripts/test_t2i_cogview.py "自定义 prompt"
"""

from __future__ import annotations

import asyncio
import mimetypes
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

# 让脚本能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("ENV", "local")

from app.config import get_settings  # noqa: E402
from app.infrastructure.ai.llm_client import LLMClient  # noqa: E402

IMAGES_DIR = Path(__file__).resolve().parent / "images"

DEFAULT_PROMPTS = [
    "A cute flat cartoon illustration of an apple, kids education style, plain white background, no text.",
    "一只戴帽子的橘色小狐狸，扁平插画风格，白底。",
]


def _slugify(text: str, max_len: int = 40) -> str:
    """把 prompt 转成安全的文件名片段。"""
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "_", text).strip("_")
    return text[:max_len] or "image"


def _ext_from_mime(mime: str, url: str) -> str:
    ext = mimetypes.guess_extension((mime or "").split(";")[0].strip())
    if ext:
        return ext
    tail = Path(url.split("?", 1)[0]).suffix
    return tail or ".png"


async def _download_and_save(url: str, prompt: str) -> Path:
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.get(url)
        resp.raise_for_status()
        payload = resp.content
        mime = resp.headers.get("content-type", "image/png")

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"{ts}_{_slugify(prompt)}{_ext_from_mime(mime, url)}"
    dest = IMAGES_DIR / fname
    dest.write_bytes(payload)
    return dest


async def _run_one(client: LLMClient, prompt: str) -> None:
    print(f"=== prompt: {prompt}")
    t0 = time.perf_counter()
    url = await client.generate_image(prompt)
    print(f"[url]     {url}")
    dest = await _download_and_save(url, prompt)
    print(f"[saved]   {dest.relative_to(Path.cwd())}"
          if dest.is_relative_to(Path.cwd())
          else f"[saved]   {dest}")
    print(f"[elapsed] {time.perf_counter() - t0:.2f}s\n")


async def main() -> None:
    settings = get_settings()
    if not settings.LLM_API_KEY:
        print("[ERROR] LLM_API_KEY 未配置，请检查 backend/.env.local")
        sys.exit(1)

    print(f"[INFO] image_model = {settings.T2I_MODEL}")
    print(f"[INFO] image_size  = {settings.T2I_SIZE}")
    print(f"[INFO] base_url    = {settings.LLM_BASE_URL}")
    print(f"[INFO] output_dir  = {IMAGES_DIR}\n")

    client = LLMClient(
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
        image_model=settings.T2I_MODEL,
        image_size=settings.T2I_SIZE,
    )

    prompts = sys.argv[1:] or DEFAULT_PROMPTS
    for p in prompts:
        try:
            await _run_one(client, p)
        except Exception as e:  # noqa: BLE001
            print(f"[FAIL] {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
