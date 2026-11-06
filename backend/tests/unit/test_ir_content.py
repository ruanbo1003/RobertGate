"""remap_draft（Agent 局部编号 → 全局 id content）与 MockIrAgent 形状单测。"""

from __future__ import annotations

import itertools

import pytest

from app.application.dto.invest_report import ChapterDraft, DraftCitation, DraftTbd
from app.application.services.ir_content import remap_draft
from app.infrastructure.ai.ir_agent_mock import MockIrAgent


def _draft() -> ChapterDraft:
    return ChapterDraft(
        paragraphs=[
            "市场规模 4,562 亿元⟦c:1⟧，公司营收 3.2 亿元⟦c:2⟧。",
            "竞对估值为⟦tbd:1⟧，详见结论章。",
        ],
        citations=[
            DraftCitation(source_type="web", title="IDC", url="https://idc.example",
                          source_id=None, page=None, quote="4,562 亿元", captured_at="2026-09"),
            DraftCitation(source_type="file", title="BP · 第 12 页", url=None,
                          source_id=11, page=12, quote="3.2 亿元", captured_at="2026-11"),
        ],
        tbds=[DraftTbd(reason="未找到竞对估值来源")],
    )


class TestRemapDraft:
    def test_maps_local_markers_to_global_ids(self):
        alloc = itertools.count(start=2100001).__next__
        content = remap_draft(_draft(), alloc)
        assert [p["id"] for p in content["paragraphs"]] == ["p1", "p2"]
        c1, c2 = content["citations"]
        assert (c1["id"], c1["n"]) == (2100001, 1)
        assert (c2["id"], c2["n"]) == (2100002, 2)
        assert f"⟦c:{c1['id']}⟧" in content["paragraphs"][0]["text"]
        assert f"⟦c:{c2['id']}⟧" in content["paragraphs"][0]["text"]
        tbd = content["tbds"][0]
        assert tbd["resolved"] is False and tbd["value"] is None
        assert f"⟦tbd:{tbd['id']}⟧" in content["paragraphs"][1]["text"]

    def test_out_of_range_markers_are_dropped(self):
        draft = _draft()
        draft.paragraphs.append("幽灵引用⟦c:9⟧与幽灵占位⟦tbd:9⟧。")
        content = remap_draft(draft, itertools.count(1).__next__)
        assert content["paragraphs"][2]["text"] == "幽灵引用与幽灵占位。"

    def test_plain_text_without_citations(self):
        draft = ChapterDraft(paragraphs=["纯文本段落。"], citations=[], tbds=[])
        content = remap_draft(draft, itertools.count(1).__next__)
        assert content["paragraphs"][0]["text"] == "纯文本段落。"
        assert content["citations"] == [] and content["tbds"] == []


class TestMockIrAgent:
    @pytest.fixture
    def agent(self) -> MockIrAgent:
        return MockIrAgent()

    async def test_learn_template_shape(self, agent):
        out = await agent.learn_template(["样本一全文", "样本二全文"], "advice")
        assert len(out.chapters) >= 3
        assert all(c.key and c.title for c in out.chapters)
        assert out.style_notes

    async def test_research_chapter_emits_events_and_draft(self, agent):
        events: list[tuple] = []
        from app.application.dto.invest_report import ResearchContext, SourceDoc

        ctx = ResearchContext(
            project_title="云帆科技 · A 轮", report_type="advice",
            chapter_key="industry", chapter_title="三、行业分析", chapter_brief="市场规模",
            style_notes="", prior_chapter_titles=[],
            sources=[SourceDoc(id=11, name="BP.pdf", text="营收 3.2 亿元")],
        )
        draft = await agent.research_chapter(ctx, lambda k, t, u: events.append((k, t, u)))
        assert len(draft.paragraphs) >= 2
        assert len(draft.citations) >= 2
        assert len(draft.tbds) == 1
        kinds = [e[0] for e in events]
        assert "search" in kinds and "write" in kinds

    async def test_chat_updates_when_chapter_given(self, agent):
        out = await agent.chat("ctx", {"title": "八、风险因素", "paragraphs": []}, "补充客户集中度风险")
        assert out.updated is True and out.paragraphs
        out2 = await agent.chat("ctx", None, "总体怎么样")
        assert out2.updated is False and out2.paragraphs is None
