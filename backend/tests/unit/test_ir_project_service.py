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
