"""法律咨询应用服务：RAG 检索 + 流式问答 + 单会话历史。

流式用例的事务边界拆成两段：用户消息在生成开始前先提交（无论后续
成败都保留提问记录），assistant 消息在流完整结束后第二次提交。
生成中途失败只产出 error 事件，不落半截回答。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from app.application.dto.legal import (
    CitationDTO,
    LawArticleDataDTO,
    LawArticleDTO,
    LegalMessageDTO,
    LegalMessagesDTO,
)
from app.application.ports import LegalChatClient, LegalKnowledgeBase
from app.domain.errors import ParamException, ServerException, codes, ensure_found
from app.domain.models.legal import (
    ROLE_ASSISTANT,
    ROLE_USER,
    LawArticle,
    LegalChatMessage,
)
from app.domain.repositories.uow import UnitOfWork

MAX_CONTENT_LEN = 2000

_SYSTEM_PROMPT = """\
你是一名基于《中华人民共和国民法典》的法律咨询助手。请遵守：
1. 仅依据下方提供的条文解读用户的问题，解释相关法律关系；引用条文时写明条文编号（如"第七百一十条"）。
2. 只做条文解读，不要给出"去起诉/去仲裁"等具体行动指引。
3. 如果提供的条文与问题无关，或问题超出民法典范围（如刑事、税务），如实说明"当前知识库仅覆盖《民法典》，该问题超出范围"，不要编造。
4. 用通俗易懂的中文回答，面向没有法律背景的普通人。

相关条文：
{articles}"""


def _event(name: str, payload: dict) -> tuple[str, dict]:
    return name, payload


class LegalConsultService:
    def __init__(
        self,
        uow: UnitOfWork,
        kb: LegalKnowledgeBase,
        chat: LegalChatClient,
        context_rounds: int = 20,
        top_k: int = 4,
    ) -> None:
        self.uow = uow
        self.kb = kb
        self.chat = chat
        self.context_rounds = context_rounds
        self.top_k = top_k

    # ---------- 校验 ----------

    def validate_content(self, content: str) -> str:
        stripped = content.strip()
        if not stripped:
            raise ParamException(codes.LEGAL_CONTENT_EMPTY, "参数缺失")
        if len(stripped) > MAX_CONTENT_LEN:
            raise ParamException(codes.LEGAL_CONTENT_TOO_LONG, "参数超长")
        return stripped

    # ---------- 查询 ----------

    async def list_messages(self, user_id: str) -> LegalMessagesDTO:
        messages = await self.uow.legal_messages.list_by_user(user_id)
        return LegalMessagesDTO(messages=[self._to_dto(m) for m in messages])

    async def clear_messages(self, user_id: str) -> None:
        await self.uow.legal_messages.delete_by_user(user_id)
        await self.uow.commit()

    async def get_article(self, article_no: int) -> LawArticleDataDTO:
        self._ensure_kb_ready()
        article = ensure_found(
            self.kb.get_article(article_no), codes.LEGAL_ARTICLE_NOT_FOUND, "条文不存在"
        )
        return LawArticleDataDTO(
            article=LawArticleDTO(
                article_no=article.article_no, label=article.label, content=article.content
            )
        )

    # ---------- 流式问答 ----------

    async def stream_reply(
        self, user_id: str, content: str
    ) -> AsyncIterator[tuple[str, dict]]:
        content = self.validate_content(content)

        history = await self.uow.legal_messages.last_n_by_user(
            user_id, self.context_rounds * 2
        )
        self._persist(user_id, ROLE_USER, content, [])
        await self.uow.commit()

        if not self.kb.ready:
            yield _event("error", {"code": codes.LEGAL_KB_NOT_READY, "message": "知识库未就绪"})
            return

        try:
            retrieved = await self.kb.retrieve(content, self.top_k)
        except Exception:
            yield _event("error", {"code": codes.LEGAL_AI_FAILED, "message": "模型服务异常"})
            return

        citations = [{"article_no": a.article_no, "label": a.label} for a in retrieved]
        yield _event("citations", {"citations": citations})

        parts: list[str] = []
        try:
            async for chunk in self.chat.stream_chat(
                self._build_messages(retrieved, history, content)
            ):
                if chunk:
                    parts.append(chunk)
                    yield _event("delta", {"text": chunk})
        except Exception:
            yield _event("error", {"code": codes.LEGAL_AI_FAILED, "message": "模型服务异常"})
            return

        assistant = self._persist(user_id, ROLE_ASSISTANT, "".join(parts), citations)
        await self.uow.commit()
        yield _event("done", {"message": self._to_dto(assistant)})

    # ---------- 内部 ----------

    def _ensure_kb_ready(self) -> None:
        if not self.kb.ready:
            raise ServerException(codes.LEGAL_KB_NOT_READY, "知识库未就绪")

    def _persist(
        self, user_id: str, role: str, content: str, citations: list[dict]
    ) -> LegalChatMessage:
        message = LegalChatMessage(
            id=str(uuid.uuid4()),
            user_id=user_id,
            role=role,
            content=content,
            citations=citations,
            created_at=datetime.now(timezone.utc),
        )
        self.uow.legal_messages.add(message)
        return message

    def _build_messages(
        self,
        retrieved: list[LawArticle],
        history: list[LegalChatMessage],
        content: str,
    ) -> list[dict[str, str]]:
        articles_text = (
            "\n\n".join(f"{a.label}　{a.content}" for a in retrieved)
            if retrieved
            else "（未检索到相关条文）"
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT.format(articles=articles_text)}
        ]
        messages.extend({"role": m.role, "content": m.content} for m in history)
        messages.append({"role": "user", "content": content})
        return messages

    @staticmethod
    def _to_dto(message: LegalChatMessage) -> LegalMessageDTO:
        return LegalMessageDTO(
            id=message.id,
            role=message.role,
            content=message.content,
            citations=[CitationDTO(**c) for c in message.citations],
            created_at=message.created_at,
        )
