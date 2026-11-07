"""IrProjectService 单测（第一批：项目/资料）。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.ir_project_service import IrProjectService
from app.domain.errors import ParamException, codes
from app.domain.models.invest_report import (
    ChapterState,
    IrChapter,
    IrProject,
    IrSource,
    IrTemplate,
    ParseState,
    TemplateStatus,
)
from app.infrastructure.ai.ir_agent_mock import MockIrAgent


class FakeStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}

    def save(self, rel_path, data):
        self.saved[rel_path] = data
        return rel_path

    def absolute(self, rel_path):
        from pathlib import Path

        return Path("/fake") / rel_path

    def delete(self, rel_path):
        self.saved.pop(rel_path, None)


class InlineRunner:
    def spawn(self, coro):
        asyncio.get_event_loop().create_task(coro)


def _ready_template() -> IrTemplate:
    t = IrTemplate.create("advice")
    t.finish_learning(
        [{"key": "industry", "title": "三、行业分析", "brief": "规模"},
         {"key": "risks", "title": "八、风险因素", "brief": "风险"}],
        "数据先行",
    )
    return t


def _project(id_: int = 1) -> IrProject:
    p = IrProject.create("云帆科技 · A 轮", "advice")
    p.id = id_
    return p


@pytest.fixture
def queue():
    q = MagicMock()
    q.counts = MagicMock(return_value=(0, 0))
    q.is_project_active = MagicMock(return_value=False)
    return q


def _stamp_ids(uow) -> None:
    counter = {"n": 100}

    def stamp(repo_name):
        def _side(entity):
            counter["n"] += 1
            if getattr(entity, "id", None) is None:
                entity.id = counter["n"]
            uow.calls.append(f"{repo_name}.add")
        return _side

    for name in ("ir_samples", "ir_templates", "ir_projects", "ir_chapters", "ir_sources", "ir_chats"):
        getattr(uow, name).add = MagicMock(side_effect=stamp(name))


@pytest.fixture
def service(uow, queue):
    _stamp_ids(uow)
    @asynccontextmanager
    async def uow_factory():
        yield uow

    return IrProjectService(
        uow=uow, agent=MockIrAgent(), queue=queue,
        storage=FakeStorage(), runner=InlineRunner(), uow_factory=uow_factory,
    )


async def test_create_project_requires_ready_template(service, uow):
    tpl = IrTemplate.create("advice")  # status=none
    uow.ir_templates.find_by_type = AsyncMock(return_value=tpl)
    with pytest.raises(ParamException) as e:
        await service.create_project("X 项目", "advice")
    assert e.value.code == codes.IR_TEMPLATE_NOT_READY


async def test_create_project_builds_chapters_from_template(service, uow):
    uow.ir_templates.find_by_type = AsyncMock(return_value=_ready_template())
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[])
    uow.ir_sources.list_by_project = AsyncMock(return_value=[])
    out = await service.create_project("云帆科技 · A 轮", "advice")
    adds = [c for c in uow.calls if c == "ir_chapters.add"]
    assert len(adds) == 2
    assert out["project"].checklist  # 资料清单引导
    assert "commit" in uow.calls


async def test_upload_source_rejects_bad_ext(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    with pytest.raises(ParamException) as e:
        await service.upload_sources(1, [("x.pptx", b"1")])
    assert e.value.code == codes.IR_PARAM_INVALID


async def test_upload_source_parses_async(service, uow, monkeypatch):
    async def fake_parse(path, agent):
        return "BP 全文", "low"

    import app.application.services.ir_project_service as mod
    monkeypatch.setattr(mod, "parse_document", fake_parse)

    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    src = IrSource.create_file(1, "bp.pdf", "p")
    src.id = 9
    uow.ir_sources.find_by_id = AsyncMock(return_value=src)

    out = await service.upload_sources(1, [("bp.pdf", b"1")])
    assert len(out) == 1
    await asyncio.sleep(0.05)
    assert src.parse_state == ParseState.READY and src.quality == "low"


async def test_add_url_source_validates(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    with pytest.raises(ParamException):
        await service.add_url_source(1, "not-a-url")


async def test_analyze_impact_only_done_chapters(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    src = IrSource.create_file(1, "新资料.pdf", "p")
    src.id = 5
    src.parse_state = ParseState.READY
    src.parsed_text = "竞对融资信息"
    uow.ir_sources.find_by_id = AsyncMock(return_value=src)
    done = IrChapter.create(1, "industry", "三、行业分析", 1)
    done.id = 31
    done.state = ChapterState.DONE
    pending = IrChapter.create(1, "risks", "八、风险因素", 2)
    pending.id = 32
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[done, pending])

    out = await service.analyze_impact(1, 5)
    assert all(i["chapter_id"] == 31 for i in out)


async def test_delete_source_keeps_chapter_citations(service, uow):
    """Review Focus #4：删资料不影响既有章节 content 里的自包含引用。"""
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    src = IrSource.create_file(1, "bp.pdf", "sources/bp.pdf")
    src.id = 5
    uow.ir_sources.find_by_id = AsyncMock(return_value=src)
    chapter = IrChapter.create(1, "industry", "三、行业分析", 1)
    chapter.content = {
        "paragraphs": [{"id": "p1", "text": "营收 3.2 亿元⟦c:1⟧"}],
        "citations": [{"id": 1, "n": 1, "source_type": "file", "title": "BP · 第 12 页",
                       "url": None, "source_id": 5, "page": 12, "quote": "3.2 亿元",
                       "captured_at": "2026-11"}],
        "tbds": [],
    }
    await service.delete_source(1, 5)
    assert "ir_sources.delete" in uow.calls
    # 引用快照自包含，不随资料删除而改动
    assert chapter.content["citations"][0]["title"] == "BP · 第 12 页"


# ---------------- 第二批：研究/状态/编辑/对话 ----------------


def _done_chapter(id_: int = 31) -> IrChapter:
    c = IrChapter.create(1, "industry", "三、行业分析", 1)
    c.id = id_
    c.state = ChapterState.DONE
    c.version = 1
    c.content = {
        "paragraphs": [
            {"id": "p1", "text": "营收 3.2 亿元⟦c:1⟧。"},
            {"id": "p2", "text": "竞对估值为⟦tbd:2⟧。"},
        ],
        "citations": [{"id": 1, "n": 1, "source_type": "file", "title": "BP", "url": None,
                       "source_id": 5, "page": 12, "quote": "3.2 亿元", "captured_at": "2026-11"}],
        "tbds": [{"id": 2, "reason": "无来源", "value": None, "resolved": False}],
    }
    return c


async def test_start_research_default_targets_not_done(service, uow, queue):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    done, pending = _done_chapter(31), IrChapter.create(1, "risks", "八、风险", 2)
    pending.id = 32
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[done, pending])
    queue.enqueue = AsyncMock(return_value=[32])
    out = await service.start_research(1, None, confirm=False)
    queue.enqueue.assert_awaited_once_with(1, [32])
    assert out == {"enqueued": [32]}


async def test_get_status_merges_queue_and_feed(service, uow, queue):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[_done_chapter(31)])
    queue.counts = MagicMock(return_value=(1, 1))
    queue.paused = False
    queue.paused_reason = None
    queue.feed = MagicMock(return_value=[{"id": 9, "chapter_id": 31, "kind": "search",
                                          "text": "t", "ref": None, "ts": "now"}])
    out = await service.get_status(1, feed_after=5)
    queue.feed.assert_called_once_with(1, 5)
    assert out["status"] == "researching"
    assert out["queue"]["pending"] == 1 and out["queue"]["running"] == 1
    assert out["chapters"][0]["tbd_count"] == 1
    assert out["feed"][0]["id"] == 9


async def test_update_paragraph_busy_2044(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    c.state = ChapterState.RESEARCHING
    uow.ir_chapters.find_by_id = AsyncMock(return_value=c)
    with pytest.raises(ParamException) as e:
        await service.update_paragraph(1, 31, "p1", "x")
    assert e.value.code == codes.IR_CHAPTER_BUSY


async def test_update_paragraph_recomputes_citation_subset(service, uow):
    """删掉正文里的 ⟦c:1⟧ 标记 → 引用从 content 中移除。"""
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    uow.ir_chapters.find_by_id = AsyncMock(return_value=c)
    out = await service.update_paragraph(1, 31, "p1", "营收 3.2 亿元（人工改写，无引用）。")
    assert out["chapter"].citations == []
    assert c.version == 2
    # tbd 仍被 p2 引用，保留
    assert len(out["chapter"].tbds) == 1


async def test_rewrite_paragraph_keeps_known_markers_only(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    uow.ir_chapters.find_by_id = AsyncMock(return_value=c)

    async def fake_rewrite(text, instruction, catalog):
        return f"重写后⟦c:1⟧，加个幽灵⟦c:999⟧。"

    service._agent.rewrite_paragraph = fake_rewrite
    out = await service.rewrite_paragraph(1, 31, "p1", "更简洁")
    p1 = next(p for p in out["chapter"].paragraphs if p["id"] == "p1")
    assert "⟦c:1⟧" in p1["text"] and "⟦c:999⟧" not in p1["text"]


async def test_resolve_tbd_updates_content(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[c])
    out = await service.resolve_tbd(1, 2, "约 12 亿元")
    text = out["chapter"].paragraphs[1]["text"]
    assert "约 12 亿元" in text and "⟦tbd:2⟧" not in text


async def test_chat_busy_chapter_2044(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    c.state = ChapterState.UPDATING
    uow.ir_chapters.find_by_id = AsyncMock(return_value=c)
    with pytest.raises(ParamException) as e:
        await service.send_chat(1, "改一下", 31)
    assert e.value.code == codes.IR_CHAPTER_BUSY


async def test_chat_applies_update_and_persists_messages(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    c = _done_chapter(31)
    uow.ir_chapters.find_by_id = AsyncMock(return_value=c)
    out = await service.send_chat(1, "补充客户集中度风险", 31)
    assert out["updated_chapter_ids"] == [31]
    assert c.version == 2
    adds = [x for x in uow.calls if x == "ir_chats.add"]
    assert len(adds) == 2  # user + assistant
