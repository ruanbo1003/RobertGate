"""invest-reports 应用层 DTO。

两类：Agent 产出 DTO（ChapterDraft 等，pydantic 校验 Agent 结构化输出）与
API 出参 DTO（SampleOut 等，Task 5 起使用）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

# ---------------- Agent 产出 ----------------


class DraftCitation(BaseModel):
    source_type: Literal["web", "file", "manual"]
    title: str
    url: str | None = None
    source_id: int | None = None
    page: int | None = None
    quote: str
    captured_at: str = ""


class DraftTbd(BaseModel):
    reason: str


class ChapterDraft(BaseModel):
    """Agent 研究产出：段落文本用局部序号标记 ⟦c:N⟧/⟦tbd:N⟧（N 从 1 计）。"""

    paragraphs: list[str] = Field(min_length=1)
    citations: list[DraftCitation] = []
    tbds: list[DraftTbd] = []


class TemplateChapterDraft(BaseModel):
    key: str
    title: str
    brief: str = ""


class TemplateDraft(BaseModel):
    chapters: list[TemplateChapterDraft] = Field(min_length=1)
    style_notes: str = ""


class ChatOutcome(BaseModel):
    reply: str
    updated: bool = False
    paragraphs: list[str] | None = None


class ImpactDraftItem(BaseModel):
    chapter_key: str
    reason: str


class ImpactDraft(BaseModel):
    items: list[ImpactDraftItem] = []


# ---------------- Agent 输入上下文 ----------------


@dataclass(frozen=True)
class SourceDoc:
    id: int
    name: str
    text: str


@dataclass(frozen=True)
class ResearchContext:
    project_title: str
    report_type: str
    chapter_key: str
    chapter_title: str
    chapter_brief: str
    style_notes: str
    prior_chapter_titles: list[str] = field(default_factory=list)
    sources: list[SourceDoc] = field(default_factory=list)
