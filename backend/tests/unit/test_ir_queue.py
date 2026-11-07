"""IrResearchQueue 单测：成功链、失败不连坐、配额暂停、feed、uow 外调用。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.application.dto.invest_report import (
    ChapterDraft,
    DraftCitation,
    ResearchContext,
)
from app.application.services.ir_queue import IrResearchQueue
from app.domain.errors import ServerException, codes
from app.domain.models.invest_report import (
    ChapterState,
    IrChapter,
    IrProject,
    IrSource,
    IrTemplate,
    ParseState,
)
from app.infrastructure.tasks import AsyncioTaskRunner


def make_store():
    project = IrProject.create("云帆科技 · A 轮", "advice")
    project.id = 1
    tpl = IrTemplate.create("advice")
    tpl.finish_learning([{"key": "industry", "title": "三、行业分析", "brief": "b"}], "style")
    chapters = {}
    for i, (key, title) in enumerate(
        [("industry", "三、行业分析"), ("risks", "八、风险因素")], start=1
    ):
        c = IrChapter.create(1, key, title, i)
        c.id = 30 + i
        chapters[c.id] = c
    src = IrSource.create_file(1, "bp.pdf", "p")
    src.id = 9
    src.parse_state = ParseState.READY
    src.parsed_text = "营收 3.2 亿元"
    return {"project": project, "template": tpl, "chapters": chapters, "sources": [src]}


class MemUow:
    def __init__(self, store):
        self.store = store
        self.ir_projects = AsyncMock()
        self.ir_projects.find_by_id = AsyncMock(return_value=store["project"])
        self.ir_chapters = AsyncMock()
        self.ir_chapters.find_by_id = AsyncMock(
            side_effect=lambda cid: store["chapters"].get(cid)
        )
        self.ir_chapters.list_by_project = AsyncMock(
            return_value=list(store["chapters"].values())
        )
        self.ir_sources = AsyncMock()
        self.ir_sources.list_by_project = AsyncMock(return_value=store["sources"])
        self.ir_templates = AsyncMock()
        self.ir_templates.find_by_type = AsyncMock(return_value=store["template"])
        self.commit = AsyncMock()


class FakeAgent:
    def __init__(self):
        self.calls: list[str] = []
        self.fail: Exception | None = None
        self.uow_open_during_call: list[int] = []

    async def research_chapter(self, ctx: ResearchContext, on_event):
        self.calls.append(ctx.chapter_key)
        on_event("search", f"检索 {ctx.chapter_title}", None)
        on_event("write", "撰写中", None)
        await asyncio.sleep(0.01)
        if self.fail is not None:
            raise self.fail
        return ChapterDraft(
            paragraphs=[f"{ctx.chapter_title} 结论⟦c:1⟧"],
            citations=[DraftCitation(source_type="web", title="IDC", url="https://x",
                                     quote="q", captured_at="2026-09")],
            tbds=[],
        )


@pytest.fixture
def store():
    return make_store()


@pytest.fixture
def agent():
    return FakeAgent()


def make_queue(store, agent, open_flag=None):
    @asynccontextmanager
    async def uow_factory():
        if open_flag is not None:
            open_flag["n"] += 1
        try:
            yield MemUow(store)
        finally:
            if open_flag is not None:
                open_flag["n"] -= 1

    return IrResearchQueue(
        uow_factory=uow_factory, agent=agent, runner=AsyncioTaskRunner(), poll_interval=0.01
    )


async def drain(queue, timeout=5.0):
    async def _wait():
        while queue.active_count > 0:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_wait(), timeout)


async def test_enqueue_runs_chapter_to_done_with_feed(store, agent):
    q = make_queue(store, agent)
    enq = await q.enqueue(1, [31])
    assert enq == [31]
    assert store["chapters"][31].state == ChapterState.RESEARCHING
    await drain(q)
    c = store["chapters"][31]
    assert c.state == ChapterState.DONE
    assert c.version == 1
    assert c.content["citations"][0]["source_type"] == "web"
    kinds = [e["kind"] for e in q.feed(1, 0)]
    assert "search" in kinds and "done" in kinds
    # feed 游标增量
    last = q.feed(1, 0)[-1]["id"]
    assert q.feed(1, last) == []


async def test_failure_does_not_cascade(store, agent):
    agent.fail = RuntimeError("boom")
    q = make_queue(store, agent)
    await q.enqueue(1, [31, 32])
    await drain(q)
    assert store["chapters"][31].state == ChapterState.FAILED
    assert store["chapters"][32].state == ChapterState.FAILED  # 各自失败，互不阻塞
    assert agent.calls == ["industry", "risks"]


async def test_quota_pauses_queue_and_reverts_pending(store, agent):
    agent.fail = ServerException(codes.IR_UPSTREAM_QUOTA, "余额不足")
    q = make_queue(store, agent)
    await q.enqueue(1, [31, 32])
    await drain(q)
    assert q.paused is True and "余额不足" in (q.paused_reason or "")
    assert store["chapters"][31].state == ChapterState.PENDING
    assert store["chapters"][32].state == ChapterState.PENDING  # 排队中的也回退
    # 再入队自动恢复
    agent.fail = None
    await q.enqueue(1, [31])
    assert q.paused is False
    await drain(q)
    assert store["chapters"][31].state == ChapterState.DONE


async def test_duplicate_enqueue_skipped(store, agent):
    q = make_queue(store, agent)
    first = await q.enqueue(1, [31])
    second = await q.enqueue(1, [31])
    assert first == [31] and second == []
    await drain(q)


async def test_cancel_reverts_queued(store, agent):
    q = make_queue(store, agent)
    await q.enqueue(1, [31, 32])
    cancelled = q.cancel_project(1)
    await drain(q)
    assert cancelled >= 0
    assert store["chapters"][32].state in (ChapterState.PENDING, ChapterState.DONE, ChapterState.FAILED)


async def test_agent_called_outside_uow(store, agent):
    open_flag = {"n": 0}
    seen = {}
    orig = agent.research_chapter

    async def patched(ctx, on_event):
        seen["open"] = open_flag["n"]
        return await orig(ctx, on_event)

    agent.research_chapter = patched
    q = make_queue(store, agent, open_flag)
    await q.enqueue(1, [31])
    await drain(q)
    assert seen["open"] == 0
