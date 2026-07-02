"""AI Client 抽象及 Mock 实现。

生产环境应将 MockAIClient 替换为真实模型 API 调用（OpenAI / Claude / Gemini 等）。
Mock 版本返回确定性、可测试的样例输出，方便前端联调和单元测试。
"""

from __future__ import annotations

from typing import Protocol


class AIClient(Protocol):
    async def translate(self, text: str) -> tuple[str, str, str]:
        """返回 (source_lang, target_lang, result)。"""
        ...

    async def grammar_correct(self, text: str) -> str: ...

    async def rewrite_native(self, text: str) -> str: ...

    async def character_info(self, char: str) -> dict:
        """返回 {pinyin, words, sentence, sentence_pinyin}."""
        ...

    async def compose_sentence(self, known_chars: list[str]) -> dict:
        """返回 {sentence, pinyin, translation}."""
        ...

    async def generate_image(self, prompt: str) -> str:
        """返回图片 URL 或路径。"""
        ...


def _is_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


class MockAIClient:
    """确定性 Mock 客户端，用于开发/测试。"""

    async def translate(self, text: str) -> tuple[str, str, str]:
        if _is_chinese(text):
            return ("zh", "en", f"[Mock EN] Translated: {text.strip()}")
        return ("en", "zh", f"[Mock 中文] 翻译：{text.strip()}")

    async def grammar_correct(self, text: str) -> str:
        return f"[Mock] Grammar-corrected: {text.strip()}"

    async def rewrite_native(self, text: str) -> str:
        return f"[Mock] Native rewrite: {text.strip()}"

    async def character_info(self, char: str) -> dict:
        return {
            "pinyin": "mó nǐ",
            "words": [f"{char}字", f"{char}文", f"{char}体"],
            "sentence": f"这是一个包含「{char}」的示例句子。",
            "sentence_pinyin": "zhè shì yī gè shì lì jù zi",
        }

    async def compose_sentence(self, known_chars: list[str]) -> dict:
        # 优先用给定字组个短句
        base = "".join(known_chars[:6]) if len(known_chars) >= 6 else "".join(known_chars)
        return {
            "sentence": base + "。",
            "pinyin": " ".join(["mó"] * len(base)),
            "translation": f"[Mock EN] Made from: {base}",
        }

    async def generate_image(self, prompt: str) -> str:
        # Mock：返回占位图片 URL。真实实现应下载并保存到 /root/images/t2i/ 下。
        safe = prompt.strip()[:40].replace(" ", "+")
        return f"https://placehold.co/1024x1024/2563EB/ffffff?text={safe}"


_default_client: AIClient | None = None


def get_ai_client() -> AIClient:
    """FastAPI 依赖：返回全局 AI 客户端。"""
    global _default_client
    if _default_client is None:
        _default_client = MockAIClient()
    return _default_client


def set_ai_client(client: AIClient) -> None:
    """测试或联调时替换全局 AI 客户端。"""
    global _default_client
    _default_client = client
