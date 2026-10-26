"""本地手工验证 LLMClient 三个翻译动作。

运行方式（在 backend/ 下）：
    ENV=local uv run python scripts/test_translate.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# 让脚本能 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("ENV", "local")

from app.config import get_settings  # noqa: E402
from app.infrastructure.ai.llm_client import LLMClient  # noqa: E402


SAMPLES = {
    "translate_zh2en": "你好世界，今天天气不错。 ",
    "translate_en2zh": "The quick brown fox jumps over the lazy dog. ",
    "grammar": "He go to school every days and play with he friends. ",
    "native": "The meeting is very good and I feel happy about the result. ",
}


async def main() -> None:
    settings = get_settings()
    if not settings.LLM_API_KEY:
        print("[ERROR] LLM_API_KEY 未配置，请检查 backend/.env.local")
        sys.exit(1)

    print(f"[INFO] model = {settings.LLM_MODEL}")
    print(f"[INFO] base_url = {settings.LLM_BASE_URL}\n")

    client = LLMClient(
        api_key=settings.LLM_API_KEY,
        model=settings.LLM_MODEL,
        base_url=settings.LLM_BASE_URL,
    )

    print("=== translate (zh -> en) ===")
    t0 = time.perf_counter()
    src, tgt, out = await client.translate(SAMPLES["translate_zh2en"])
    print(f"[{src} -> {tgt}] {out}")
    print(f"[elapsed] {time.perf_counter() - t0:.2f}s\n")

    print("=== translate (en -> zh) ===")
    t0 = time.perf_counter()
    src, tgt, out = await client.translate(SAMPLES["translate_en2zh"])
    print(f"[{src} -> {tgt}] {out}")
    print(f"[elapsed] {time.perf_counter() - t0:.2f}s\n")

    print("=== grammar ===")
    t0 = time.perf_counter()
    out = await client.grammar_correct(SAMPLES["grammar"])
    print(out)
    print(f"[elapsed] {time.perf_counter() - t0:.2f}s\n")

    print("=== native ===")
    t0 = time.perf_counter()
    out = await client.rewrite_native(SAMPLES["native"])
    print(out)
    print(f"[elapsed] {time.perf_counter() - t0:.2f}s\n")


if __name__ == "__main__":
    asyncio.run(main())
