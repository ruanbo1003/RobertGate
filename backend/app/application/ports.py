"""AI Client 抽象（应用层端口）。

具体实现（Mock / 真实 LLM）及全局单例装配在 infrastructure/ai/ 下，
本模块只定义契约，不得反向 import infrastructure。
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
