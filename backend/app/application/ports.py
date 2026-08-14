"""应用层端口（AI Client / 密码哈希 / 令牌）。

具体实现及全局单例装配在 infrastructure/ 下，
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


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...


class TokenProvider(Protocol):
    def create(self, user_id: str) -> str:
        """签发访问令牌。"""
        ...

    def decode(self, token: str) -> str | None:
        """解出 user_id；令牌非法或过期返回 None。"""
        ...

    @property
    def ttl_seconds(self) -> int:
        """令牌有效期（秒），用于 login/register 的 expires_in。"""
        ...
