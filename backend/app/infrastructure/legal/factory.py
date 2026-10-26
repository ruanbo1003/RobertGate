"""法律咨询基础设施装配：知识库与对话客户端的全局单例。

复用全局 LLM 凭据（LLM_API_KEY / LLM_BASE_URL，当前为 SiliconFlow）：
配置了 Key 时走真实 DeepSeek 对话 + BGE-M3 向量，
否则退化为 Mock（条文查询仍可用，检索降级、回答为固定提示）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.application.ports import LegalChatClient, LegalKnowledgeBase


class BuildableKB(LegalKnowledgeBase, Protocol):
    async def build_index(self) -> None: ...


_kb: BuildableKB | None = None
_chat: LegalChatClient | None = None


def get_legal_kb() -> BuildableKB:
    global _kb
    if _kb is not None:
        return _kb

    from app.config import get_settings
    from app.infrastructure.legal.knowledge_base import MockLegalKB, SiliconFlowLegalKB

    settings = get_settings()
    pdf_path = Path(settings.LEGAL_PDF_PATH)
    if settings.LLM_API_KEY:
        _kb = SiliconFlowLegalKB(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            embedding_model=settings.LEGAL_EMBEDDING_MODEL,
            pdf_path=pdf_path,
            index_path=Path(settings.LEGAL_INDEX_PATH),
            min_score=settings.LEGAL_MIN_SCORE,
        )
    else:
        _kb = MockLegalKB(pdf_path=pdf_path)
    return _kb


def get_legal_chat() -> LegalChatClient:
    global _chat
    if _chat is not None:
        return _chat

    from app.config import get_settings
    from app.infrastructure.legal.chat_client import MockLegalChat, SiliconFlowLegalChat

    settings = get_settings()
    if settings.LLM_API_KEY:
        _chat = SiliconFlowLegalChat(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            model=settings.LEGAL_CHAT_MODEL,
        )
    else:
        _chat = MockLegalChat()
    return _chat


def set_legal_kb(kb: BuildableKB) -> None:
    """测试或联调时替换全局知识库。"""
    global _kb
    _kb = kb


def set_legal_chat(chat: LegalChatClient) -> None:
    """测试或联调时替换全局对话客户端。"""
    global _chat
    _chat = chat
