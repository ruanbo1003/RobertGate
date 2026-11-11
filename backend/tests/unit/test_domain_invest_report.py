"""invest-reports 领域模型单测：章节状态机、项目状态聚合、tbd 解决、标记剥离。"""

from __future__ import annotations

import pytest

from app.domain.errors import ParamException, codes
from app.domain.models.invest_report import (
    ChapterState,
    IrChapter,
    derive_project_status,
    resolve_tbd_in_content,
    strip_markers,
    unresolved_tbds,
)


def _chapter(state: str = ChapterState.PENDING) -> IrChapter:
    c = IrChapter.create(project_id=1, key="industry", title="三、行业分析", order_index=3)
    c.state = state
    return c


CONTENT = {
    "paragraphs": [
        {"id": "p1", "text": "市场规模 4,562 亿元⟦c:101⟧，竞对估值为⟦tbd:7⟧。"},
    ],
    "citations": [
        {"id": 101, "n": 1, "source_type": "web", "title": "IDC", "url": "https://x",
         "source_id": None, "page": None, "quote": "4,562 亿元", "captured_at": "2026-09"},
    ],
    "tbds": [{"id": 7, "reason": "未找到可靠来源", "value": None, "resolved": False}],
}


class TestChapterStateMachine:
    def test_create_defaults(self):
        c = _chapter()
        assert c.state == ChapterState.PENDING
        assert c.version == 0
        assert c.content == {"paragraphs": [], "citations": [], "tbds": []}

    def test_mark_researching_from_pending(self):
        c = _chapter()
        c.mark_researching()
        assert c.state == ChapterState.RESEARCHING

    def test_mark_researching_from_stale_becomes_updating(self):
        c = _chapter(ChapterState.STALE)
        c.mark_researching()
        assert c.state == ChapterState.UPDATING

    def test_mark_researching_busy_raises_2044(self):
        for st in (ChapterState.RESEARCHING, ChapterState.UPDATING):
            c = _chapter(st)
            with pytest.raises(ParamException) as e:
                c.mark_researching()
            assert e.value.code == codes.IR_CHAPTER_BUSY

    def test_mark_done_sets_content_and_bumps_version(self):
        c = _chapter(ChapterState.RESEARCHING)
        c.error = "old"
        c.mark_done(CONTENT)
        assert c.state == ChapterState.DONE
        assert c.version == 1
        assert c.error is None
        assert c.content["citations"][0]["id"] == 101

    def test_mark_failed_and_pending(self):
        c = _chapter(ChapterState.RESEARCHING)
        c.mark_failed("boom")
        assert c.state == ChapterState.FAILED and c.error == "boom"
        c2 = _chapter(ChapterState.RESEARCHING)
        c2.mark_pending()
        assert c2.state == ChapterState.PENDING and c2.error is None


class TestProjectStatus:
    def test_four_states(self):
        mk = lambda *sts: [_chapter(s) for s in sts]
        assert derive_project_status(mk(ChapterState.PENDING), queue_active=False) == "draft"
        assert derive_project_status(mk(ChapterState.PENDING), queue_active=True) == "researching"
        assert derive_project_status(mk(ChapterState.RESEARCHING, ChapterState.DONE), queue_active=False) == "researching"
        assert derive_project_status(mk(ChapterState.FAILED, ChapterState.DONE), queue_active=False) == "partial_failed"
        assert derive_project_status(mk(ChapterState.DONE, ChapterState.DONE), queue_active=False) == "completed"


class TestTbd:
    def test_unresolved_tbds(self):
        assert unresolved_tbds(CONTENT) == [CONTENT["tbds"][0]]

    def test_resolve_replaces_marker_and_adds_manual_citation(self):
        out = resolve_tbd_in_content(CONTENT, 7, "约 12 亿元")
        text = out["paragraphs"][0]["text"]
        assert "⟦tbd:7⟧" not in text
        assert "约 12 亿元" in text
        manual = [c for c in out["citations"] if c["source_type"] == "manual"]
        assert len(manual) == 1
        assert f"⟦c:{manual[0]['id']}⟧" in text
        tbd = out["tbds"][0]
        assert tbd["resolved"] is True and tbd["value"] == "约 12 亿元"
        # 原 content 不被修改
        assert "⟦tbd:7⟧" in CONTENT["paragraphs"][0]["text"]

    def test_resolve_unknown_tbd_raises(self):
        with pytest.raises(ParamException) as e:
            resolve_tbd_in_content(CONTENT, 999, "x")
        assert e.value.code == codes.IR_NOT_FOUND


def test_strip_markers():
    assert strip_markers("A⟦c:101⟧B⟦tbd:7⟧C") == "ABC"
