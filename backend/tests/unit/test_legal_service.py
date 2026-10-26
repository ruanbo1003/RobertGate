"""LegalConsultService 单元测试：内容校验、SSE 事件流、历史窗口、条文查询。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone

import pytest

from app.application.services.legal_service import LegalConsultService
from app.domain.errors import ParamException, ServerException, codes
from app.domain.models.legal import LawArticle, LegalChatMessage


def make_message(
    role: str = "user",
    content: str = "问题",
    citations: list[dict] | None = None,
    msg_id: str = "m-1",
) -> LegalChatMessage:
    return LegalChatMessage(
        id=msg_id,
        user_id="u-1",
        role=role,
        content=content,
        citations=citations or [],
        created_at=datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc),
    )


ARTICLE_710 = LawArticle(article_no=710, label="第七百一十条", content="承租人不承担赔偿责任。")
ARTICLE_708 = LawArticle(article_no=708, label="第七百零八条", content="出租人应当交付租赁物。")


class FakeKB:
    def __init__(
        self,
        retrieved: list[LawArticle] | None = None,
        articles: dict[int, LawArticle] | None = None,
        ready: bool = True,
    ) -> None:
        self.retrieved = retrieved if retrieved is not None else []
        self.articles = articles or {}
        self._ready = ready
        self.queries: list[str] = []

    @property
    def ready(self) -> bool:
        return self._ready

    async def retrieve(self, query: str, top_k: int) -> list[LawArticle]:
        self.queries.append(query)
        return self.retrieved[:top_k]

    def get_article(self, article_no: int) -> LawArticle | None:
        return self.articles.get(article_no)


class FakeChat:
    def __init__(self, chunks: list[str] | None = None, fail: bool = False) -> None:
        self.chunks = chunks if chunks is not None else ["答", "案"]
        self.fail = fail
        self.received_messages: list[dict[str, str]] | None = None

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        self.received_messages = messages
        if self.fail:
            raise RuntimeError("upstream down")
        for chunk in self.chunks:
            yield chunk


def make_service(
    uow,
    kb: FakeKB | None = None,
    chat: FakeChat | None = None,
    context_rounds: int = 20,
) -> LegalConsultService:
    return LegalConsultService(
        uow=uow,
        kb=kb or FakeKB(),
        chat=chat or FakeChat(),
        context_rounds=context_rounds,
        top_k=4,
    )


async def collect(gen) -> list[tuple[str, dict]]:
    return [event async for event in gen]


class TestValidateContent:
    def test_empty_content_raises_2001(self, uow) -> None:
        service = make_service(uow)
        with pytest.raises(ParamException) as e:
            service.validate_content("   ")
        assert e.value.code == codes.LEGAL_CONTENT_EMPTY

    def test_too_long_content_raises_2003(self, uow) -> None:
        service = make_service(uow)
        with pytest.raises(ParamException) as e:
            service.validate_content("问" * 2001)
        assert e.value.code == codes.LEGAL_CONTENT_TOO_LONG

    def test_strips_whitespace(self, uow) -> None:
        service = make_service(uow)
        assert service.validate_content("  问题  ") == "问题"


class TestStreamReply:
    async def test_happy_path_event_order_and_persistence(self, uow) -> None:
        uow.legal_messages.last_n_by_user.return_value = []
        kb = FakeKB(retrieved=[ARTICLE_710, ARTICLE_708])
        chat = FakeChat(chunks=["你", "好"])
        service = make_service(uow, kb=kb, chat=chat)

        events = await collect(service.stream_reply("u-1", "押金不退怎么办"))

        names = [name for name, _ in events]
        assert names[0] == "citations"
        assert names[-1] == "done"
        assert all(n == "delta" for n in names[1:-1])

        assert events[0][1]["citations"] == [
            {"article_no": 710, "label": "第七百一十条"},
            {"article_no": 708, "label": "第七百零八条"},
        ]
        assert "".join(p["text"] for n, p in events if n == "delta") == "你好"

        done_msg = events[-1][1]["message"]
        assert done_msg.role == "assistant"
        assert done_msg.content == "你好"
        assert [c.article_no for c in done_msg.citations] == [710, 708]

        # 用户消息先落库提交，assistant 流完再落库提交
        assert uow.calls == [
            "legal_messages.add",
            "commit",
            "legal_messages.add",
            "commit",
        ]

    async def test_history_window_limits_to_context_rounds(self, uow) -> None:
        history = [
            make_message(role="user" if i % 2 == 0 else "assistant", content=f"消息{i}")
            for i in range(10)
        ]
        uow.legal_messages.last_n_by_user.return_value = history
        chat = FakeChat()
        service = make_service(uow, chat=chat, context_rounds=3)

        await collect(service.stream_reply("u-1", "新问题"))

        uow.legal_messages.last_n_by_user.assert_awaited_once_with("u-1", 6)
        assert chat.received_messages is not None
        assert chat.received_messages[-1] == {"role": "user", "content": "新问题"}

    async def test_system_prompt_contains_retrieved_articles(self, uow) -> None:
        uow.legal_messages.last_n_by_user.return_value = []
        kb = FakeKB(retrieved=[ARTICLE_710])
        chat = FakeChat()
        service = make_service(uow, kb=kb, chat=chat)

        await collect(service.stream_reply("u-1", "问题"))

        assert chat.received_messages is not None
        system = chat.received_messages[0]
        assert system["role"] == "system"
        assert "第七百一十条" in system["content"]
        assert "承租人不承担赔偿责任。" in system["content"]

    async def test_kb_not_ready_yields_5002_after_saving_user_message(self, uow) -> None:
        uow.legal_messages.last_n_by_user.return_value = []
        service = make_service(uow, kb=FakeKB(ready=False))

        events = await collect(service.stream_reply("u-1", "问题"))

        assert events[-1][0] == "error"
        assert events[-1][1]["code"] == codes.LEGAL_KB_NOT_READY
        assert uow.calls == ["legal_messages.add", "commit"]

    async def test_chat_failure_yields_5001_and_skips_assistant_persist(self, uow) -> None:
        uow.legal_messages.last_n_by_user.return_value = []
        service = make_service(uow, chat=FakeChat(fail=True))

        events = await collect(service.stream_reply("u-1", "问题"))

        assert events[-1][0] == "error"
        assert events[-1][1]["code"] == codes.LEGAL_AI_FAILED
        assert uow.calls == ["legal_messages.add", "commit"]

    async def test_empty_retrieval_yields_empty_citations(self, uow) -> None:
        uow.legal_messages.last_n_by_user.return_value = []
        service = make_service(uow, kb=FakeKB(retrieved=[]))

        events = await collect(service.stream_reply("u-1", "怎么报税"))

        assert events[0] == ("citations", {"citations": []})
        assert events[-1][0] == "done"


class TestListAndClear:
    async def test_list_messages_maps_to_dto(self, uow) -> None:
        uow.legal_messages.list_by_user.return_value = [
            make_message(
                role="assistant",
                content="回答",
                citations=[{"article_no": 710, "label": "第七百一十条"}],
                msg_id="m-2",
            )
        ]
        service = make_service(uow)

        data = await service.list_messages("u-1")

        assert len(data.messages) == 1
        msg = data.messages[0]
        assert msg.id == "m-2"
        assert msg.citations[0].label == "第七百一十条"

    async def test_clear_messages_deletes_and_commits(self, uow) -> None:
        service = make_service(uow)

        await service.clear_messages("u-1")

        uow.legal_messages.delete_by_user.assert_awaited_once_with("u-1")
        uow.commit.assert_awaited_once()


class TestGetArticle:
    async def test_found_returns_dto(self, uow) -> None:
        kb = FakeKB(articles={710: ARTICLE_710})
        service = make_service(uow, kb=kb)

        data = await service.get_article(710)

        assert data.article.article_no == 710
        assert data.article.content == "承租人不承担赔偿责任。"

    async def test_missing_raises_2010(self, uow) -> None:
        service = make_service(uow, kb=FakeKB(articles={}))
        with pytest.raises(ParamException) as e:
            await service.get_article(999999)
        assert e.value.code == codes.LEGAL_ARTICLE_NOT_FOUND

    async def test_kb_not_ready_raises_5002(self, uow) -> None:
        service = make_service(uow, kb=FakeKB(ready=False))
        with pytest.raises(ServerException) as e:
            await service.get_article(710)
        assert e.value.code == codes.LEGAL_KB_NOT_READY
