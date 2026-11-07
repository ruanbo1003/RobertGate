"""Word 导出单测：干净稿、tbd 阻断、无成稿报错。"""

from __future__ import annotations

import io
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from docx import Document

from app.application.services.ir_project_service import IrProjectService
from app.domain.errors import ParamException, codes
from app.domain.models.invest_report import ChapterState, IrChapter, IrProject
from app.infrastructure.ai.ir_agent_mock import MockIrAgent
from app.infrastructure.ir_export import build_docx


def test_build_docx_contains_titles_and_no_markers():
    data = build_docx(
        "云帆科技 · A 轮", "advice",
        [{"title": "三、行业分析", "paragraphs": ["规模 4,562 亿元。", "增速 28.3%。"]}],
    )
    doc = Document(io.BytesIO(data))
    texts = [p.text for p in doc.paragraphs]
    assert any("云帆科技" in t for t in texts)
    assert any("三、行业分析" in t for t in texts)
    assert all("⟦" not in t for t in texts)


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


def _project():
    p = IrProject.create("云帆科技 · A 轮", "advice")
    p.id = 1
    return p


def _chapter(with_tbd: bool):
    c = IrChapter.create(1, "industry", "三、行业分析", 1)
    c.id = 31
    c.state = ChapterState.DONE
    c.content = {
        "paragraphs": [{"id": "p1", "text": "规模 4,562 亿元⟦c:1⟧" + ("，估值⟦tbd:2⟧" if with_tbd else "")}],
        "citations": [{"id": 1, "n": 1, "source_type": "web", "title": "IDC", "url": "https://x",
                       "source_id": None, "page": None, "quote": "q", "captured_at": "2026-09"}],
        "tbds": [{"id": 2, "reason": "无来源", "value": None, "resolved": False}] if with_tbd else [],
    }
    return c


@pytest.fixture
def service(uow):
    @asynccontextmanager
    async def uow_factory():
        yield uow

    queue = MagicMock()
    queue.counts = MagicMock(return_value=(0, 0))
    class _P:
        async def parse_document(self, path, agent):
            return "", "ok"

        async def parse_url(self, url):
            return ""

    return IrProjectService(
        uow=uow, agent=MockIrAgent(), queue=queue,
        storage=FakeStorage(), runner=MagicMock(), uow_factory=uow_factory,
        parser=_P(), exporter=build_docx,
    )


async def test_export_blocked_by_unresolved_tbd(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[_chapter(with_tbd=True)])
    with pytest.raises(ParamException) as e:
        await service.export(1)
    assert e.value.code == codes.IR_EXPORT_BLOCKED
    assert e.value.data["pending"][0]["chapter_id"] == 31


async def test_export_requires_done_chapters(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    pending = IrChapter.create(1, "x", "一", 1)
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[pending])
    with pytest.raises(ParamException) as e:
        await service.export(1)
    assert e.value.code == codes.IR_NOT_FOUND


async def test_export_writes_clean_docx(service, uow):
    uow.ir_projects.find_by_id = AsyncMock(return_value=_project())
    uow.ir_chapters.list_by_project = AsyncMock(return_value=[_chapter(with_tbd=False)])
    out = await service.export(1)
    assert out["download_url"].endswith("/projects/1/download")
    data = service._storage.saved["projects/1/final.docx"]
    doc = Document(io.BytesIO(data))
    assert all("⟦" not in p.text for p in doc.paragraphs)
