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

    async def practice_text(self, learned_chars: list[str]) -> dict:
        """返回 {text, annotations: [{char, pinyin}], new_chars: [char]}."""
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

    async def practice_text(self, learned_chars: list[str]) -> dict:
        base = "".join(learned_chars[:8]) if learned_chars else "字"
        text = f"今天{base}都很好。"
        annotations = [
            {"char": ch, "pinyin": "mó"}
            for ch in text
            if "\u4e00" <= ch <= "\u9fff"
        ]
        return {"text": text, "annotations": annotations, "new_chars": []}

    async def generate_image(self, prompt: str) -> str:
        # Mock：返回占位图片 URL。真实实现应下载并保存到 /root/images/t2i/ 下。
        safe = prompt.strip()[:40].replace(" ", "+")
        return f"https://placehold.co/1024x1024/2563EB/ffffff?text={safe}"


_default_client: AIClient | None = None


def get_ai_client() -> AIClient:
    """FastAPI 依赖：返回全局 AI 客户端。

    配置了 LLM_API_KEY 时使用 LLMClient（LangChain 接入任意 OpenAI 兼容模型：
    智谱 BigModel / OpenRouter / DeepSeek / OpenAI 等），
    否则回退到 MockAIClient，保证本地无 key 环境仍可运行。
    """
    global _default_client
    if _default_client is not None:
        return _default_client

    from app.core.setting import get_settings

    settings = get_settings()
    if settings.LLM_API_KEY:
        # 延迟导入，避免未安装 langchain 时也能启动 mock 模式
        from app.service.llm_client import LLMClient

        _default_client = LLMClient(
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
            base_url=settings.LLM_BASE_URL,
            image_model=settings.T2I_MODEL,
            image_size=settings.T2I_SIZE,
        )
    else:
        _default_client = MockAIClient()
    return _default_client


def set_ai_client(client: AIClient) -> None:
    """测试或联调时替换全局 AI 客户端。"""
    global _default_client
    _default_client = client
