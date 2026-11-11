"""invest-reports 请求 Schema（出参见 application/dto/invest_report.py）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LearnTemplateRequest(BaseModel):
    sample_ids: list[int] | None = None


class TemplateChapterIn(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    brief: str = Field(default="", max_length=1000)


class UpdateTemplateRequest(BaseModel):
    chapters: list[TemplateChapterIn] = Field(min_length=1)
    style_notes: str | None = Field(default=None, max_length=4000)


class CreateProjectRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    type: str = Field(pattern="^(advice|dd)$")


class AddUrlSourceRequest(BaseModel):
    url: str = Field(min_length=8, max_length=1024)


class ResearchRequest(BaseModel):
    chapter_ids: list[int] | None = None
    confirm: bool = False


class UpdateParagraphRequest(BaseModel):
    text: str = Field(max_length=20000)


class RewriteParagraphRequest(BaseModel):
    instruction: str = Field(min_length=1, max_length=1000)


class ResolveTbdRequest(BaseModel):
    value: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    chapter_id: int | None = None
