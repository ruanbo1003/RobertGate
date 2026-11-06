"""invest-reports Mock Agent：无 Key 环境的确定性实现，保证全链路可走通。"""

from __future__ import annotations

import asyncio
from typing import Callable

from app.application.dto.invest_report import (
    ChapterDraft,
    ChatOutcome,
    DraftCitation,
    DraftTbd,
    ImpactDraft,
    ImpactDraftItem,
    ResearchContext,
    TemplateChapterDraft,
    TemplateDraft,
)

_MOCK_CHAPTERS = [
    ("overview", "一、交易概览", "交易结构与估值要点"),
    ("company", "二、公司概况", "历史沿革与核心产品"),
    ("industry", "三、行业分析", "市场规模与增速"),
    ("risks", "四、风险因素", "经营与合规风险"),
    ("conclusion", "五、结论", "建议与分级"),
]


class MockIrAgent:
    async def learn_template(self, samples_text: list[str], report_type: str) -> TemplateDraft:
        await asyncio.sleep(0.05)
        return TemplateDraft(
            chapters=[TemplateChapterDraft(key=k, title=t, brief=b) for k, t, b in _MOCK_CHAPTERS],
            style_notes="数据先行，每章末小结。（mock）",
        )

    async def research_chapter(
        self, ctx: ResearchContext, on_event: Callable[[str, str, str | None], None]
    ) -> ChapterDraft:
        on_event("search", f"检索「{ctx.project_title} {ctx.chapter_title}」", None)
        await asyncio.sleep(0.02)
        on_event("read_url", "读取行业报告页（mock）", "https://example.com/report")
        if ctx.sources:
            on_event("read_source", f"从「{ctx.sources[0].name}」提取数据", None)
        on_event("write", "正在撰写本章初稿…", None)
        await asyncio.sleep(0.02)
        source_id = ctx.sources[0].id if ctx.sources else None
        return ChapterDraft(
            paragraphs=[
                f"{ctx.chapter_title}：市场保持高速增长，2025 年规模达 4,562 亿元⟦c:1⟧。",
                "公司 2025 年营收 3.2 亿元⟦c:2⟧；竞对最新估值为⟦tbd:1⟧。",
            ],
            citations=[
                DraftCitation(source_type="web", title="IDC · 行业市场跟踪",
                              url="https://example.com/report", quote="规模达 4,562 亿元",
                              captured_at="2026-09"),
                DraftCitation(source_type="file", title="BP · 财务摘要", source_id=source_id,
                              page=12, quote="2025 年营收 3.2 亿元", captured_at="2026-11"),
            ],
            tbds=[DraftTbd(reason="未找到竞对最新估值的可靠来源")],
        )

    async def rewrite_paragraph(
        self, paragraph_text: str, instruction: str, citations_catalog: list[dict]
    ) -> str:
        await asyncio.sleep(0.02)
        return f"（按指令「{instruction}」重写）{paragraph_text}"

    async def chat(self, ctx_summary: str, chapter: dict | None, message: str) -> ChatOutcome:
        await asyncio.sleep(0.02)
        if chapter is not None:
            existing = [p["text"] for p in chapter.get("paragraphs", [])]
            return ChatOutcome(
                reply=f"已按你的意见更新「{chapter.get('title', '')}」。",
                updated=True,
                paragraphs=[*existing, f"（按对话补充）{message[:60]}"],
            )
        return ChatOutcome(reply="好的，已理解。如需改稿请指定章节。", updated=False, paragraphs=None)

    async def analyze_impact(self, source_text: str, done_chapters: list[dict]) -> ImpactDraft:
        await asyncio.sleep(0.02)
        return ImpactDraft(
            items=[
                ImpactDraftItem(chapter_key=c["key"], reason="新资料包含与本章相关的数据（mock）")
                for c in done_chapters[:2]
            ]
        )

    async def parse_image(self, image_bytes: bytes, hint: str) -> str:
        await asyncio.sleep(0.02)
        return f"（mock OCR）{hint}：识别到 {len(image_bytes)} 字节图像内容。"
