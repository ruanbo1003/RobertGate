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


# ---------------- API 出参 DTO ----------------


class DTO(BaseModel):
    model_config = {"from_attributes": True}


class SampleOut(DTO):
    id: int
    type: str
    filename: str
    parse_state: str
    uploaded_at: str

    @classmethod
    def build(cls, s) -> "SampleOut":
        return cls(id=s.id, type=s.type, filename=s.filename,
                   parse_state=s.parse_state, uploaded_at=s.uploaded_at.isoformat())


class TemplateOut(DTO):
    type: str
    status: str
    chapters: list[dict]
    style_notes: str
    learned_from: list[int]
    error: str | None
    updated_at: str

    @classmethod
    def build(cls, t) -> "TemplateOut":
        return cls(type=t.type, status=t.status, chapters=list(t.chapters),
                   style_notes=t.style_notes, learned_from=list(t.learned_from),
                   error=t.error, updated_at=t.updated_at.isoformat())


class LibraryGroupOut(DTO):
    template: TemplateOut | None
    samples: list[SampleOut]


class LibraryOut(DTO):
    advice: LibraryGroupOut
    dd: LibraryGroupOut


class SourceOut(DTO):
    id: int
    kind: str
    filename: str | None
    url: str | None
    parse_state: str
    quality: str
    uploaded_at: str

    @classmethod
    def build(cls, s) -> "SourceOut":
        return cls(id=s.id, kind=s.kind, filename=s.filename, url=s.url,
                   parse_state=s.parse_state, quality=s.quality,
                   uploaded_at=s.uploaded_at.isoformat())


class ChapterMetaOut(DTO):
    id: int
    key: str
    title: str
    state: str
    error: str | None
    tbd_count: int
    version: int

    @classmethod
    def build(cls, c) -> "ChapterMetaOut":
        from app.domain.models.invest_report import unresolved_tbds

        return cls(id=c.id, key=c.key, title=c.title, state=c.state, error=c.error,
                   tbd_count=len(unresolved_tbds(c.content)), version=c.version)


class ProjectSummaryOut(DTO):
    id: int
    title: str
    type: str
    status: str
    chapters_done: int
    chapters_total: int
    tbd_count: int
    updated_at: str


class ProjectDetailOut(ProjectSummaryOut):
    chapters: list[ChapterMetaOut]
    sources: list[SourceOut]
    checklist: list[str]


class ChapterDetailOut(ChapterMetaOut):
    paragraphs: list[dict]
    citations: list[dict]
    tbds: list[dict]

    @classmethod
    def build(cls, c) -> "ChapterDetailOut":
        meta = ChapterMetaOut.build(c)
        return cls(
            **meta.model_dump(),
            paragraphs=list(c.content.get("paragraphs", [])),
            citations=list(c.content.get("citations", [])),
            tbds=list(c.content.get("tbds", [])),
        )
