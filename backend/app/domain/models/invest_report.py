"""invest-reports（投资报告 Agent）领域模型。

实体：范本、模板档案、项目、章节（正文 content JSONB：paragraphs/citations/tbds，
正文内联标记 ⟦c:引用id⟧ / ⟦tbd:id⟧）、资料、对话消息。
章节状态机与 tbd 解决等不变量收在本模块；对应 docs/api/invest-reports.md。
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.errors import ParamException, codes
from app.domain.models.base import Base

REPORT_TYPES = ("advice", "dd")
TITLE_MAX = 100
SAMPLE_EXTS = (".docx",)
SOURCE_EXTS = (".docx", ".pdf", ".xlsx", ".png", ".jpg", ".jpeg")
UPLOAD_MAX_BYTES = 50 * 1024 * 1024

_MARKER_RE = re.compile(r"⟦(?:c|tbd):\d+⟧")


class ChapterState(StrEnum):
    PENDING = "pending"
    RESEARCHING = "researching"
    DONE = "done"
    FAILED = "failed"
    STALE = "stale"
    UPDATING = "updating"


class ParseState(StrEnum):
    PENDING = "pending"
    PARSING = "parsing"
    READY = "ready"
    FAILED = "failed"


class TemplateStatus(StrEnum):
    NONE = "none"
    LEARNING = "learning"
    READY = "ready"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_content() -> dict:
    return {"paragraphs": [], "citations": [], "tbds": []}


def validate_report_type(value: str) -> str:
    if value not in REPORT_TYPES:
        raise ParamException(codes.IR_PARAM_INVALID, f"未知报告类型：{value}")
    return value


# ---------------- 范本与模板 ----------------


class IrSample(Base):
    __tablename__ = "ir_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(255))
    parse_state: Mapped[str] = mapped_column(String(16), default=ParseState.PENDING)
    parsed_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def create(cls, type_: str, filename: str, file_path: str) -> IrSample:
        return cls(
            type=validate_report_type(type_),
            filename=filename,
            file_path=file_path,
            parse_state=ParseState.PARSING,
            parsed_text="",
            uploaded_at=_now(),
        )


class IrTemplate(Base):
    __tablename__ = "ir_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=TemplateStatus.NONE)
    chapters: Mapped[list] = mapped_column(JSONB, default=list)
    style_notes: Mapped[str] = mapped_column(Text, default="")
    learned_from: Mapped[list] = mapped_column(JSONB, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def create(cls, type_: str) -> IrTemplate:
        return cls(
            type=validate_report_type(type_),
            status=TemplateStatus.NONE,
            chapters=[],
            style_notes="",
            learned_from=[],
            error=None,
            updated_at=_now(),
        )

    def start_learning(self, sample_ids: list[int]) -> None:
        self.status = TemplateStatus.LEARNING
        self.learned_from = list(sample_ids)
        self.error = None
        self.updated_at = _now()

    def finish_learning(self, chapters: list[dict], style_notes: str) -> None:
        self.status = TemplateStatus.READY
        self.chapters = chapters
        self.style_notes = style_notes
        self.updated_at = _now()

    def fail_learning(self, error: str) -> None:
        self.status = TemplateStatus.FAILED
        self.error = error[:500]
        self.updated_at = _now()


# ---------------- 项目与章节 ----------------


class IrProject(Base):
    __tablename__ = "ir_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(TITLE_MAX))
    type: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(cls, title: str, type_: str) -> IrProject:
        title = (title or "").strip()
        if not title:
            raise ParamException(codes.IR_PARAM_INVALID, "报告名称不能为空")
        if len(title) > TITLE_MAX:
            raise ParamException(codes.IR_PARAM_INVALID, f"报告名称超长（最大 {TITLE_MAX} 字符）")
        now = _now()
        return cls(title=title, type=validate_report_type(type_), created_at=now, updated_at=now)

    def touch(self) -> None:
        self.updated_at = _now()


class IrChapter(Base):
    __tablename__ = "ir_chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ir_projects.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    order_index: Mapped[int] = mapped_column(Integer, index=True)
    state: Mapped[str] = mapped_column(String(16), default=ChapterState.PENDING)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[dict] = mapped_column(JSONB, default=_empty_content)

    @classmethod
    def create(cls, project_id: int, key: str, title: str, order_index: int) -> IrChapter:
        return cls(
            project_id=project_id,
            key=key,
            title=title,
            order_index=order_index,
            state=ChapterState.PENDING,
            error=None,
            version=0,
            content=_empty_content(),
        )

    # ---- 状态机 ----

    def ensure_not_busy(self) -> None:
        if self.state in (ChapterState.RESEARCHING, ChapterState.UPDATING):
            raise ParamException(codes.IR_CHAPTER_BUSY, "章节正在研究/更新中")

    def mark_researching(self) -> None:
        self.ensure_not_busy()
        self.state = (
            ChapterState.UPDATING if self.state == ChapterState.STALE else ChapterState.RESEARCHING
        )
        self.error = None

    def mark_done(self, content: dict) -> None:
        self.state = ChapterState.DONE
        self.content = content
        self.version += 1
        self.error = None

    def mark_failed(self, error: str) -> None:
        self.state = ChapterState.FAILED
        self.error = error[:500]

    def mark_pending(self) -> None:
        self.state = ChapterState.PENDING
        self.error = None

    def mark_stale(self) -> None:
        if self.state == ChapterState.DONE:
            self.state = ChapterState.STALE

    def bump_version(self, content: dict) -> None:
        """人工编辑/对话改稿落 content（状态不变）。"""
        self.content = content
        self.version += 1


# ---------------- 资料与对话 ----------------


class IrSource(Base):
    __tablename__ = "ir_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ir_projects.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(8))  # file | url
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parse_state: Mapped[str] = mapped_column(String(16), default=ParseState.PENDING)
    quality: Mapped[str] = mapped_column(String(8), default="ok")  # ok | low
    parsed_text: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def create_file(cls, project_id: int, filename: str, file_path: str) -> IrSource:
        return cls(
            project_id=project_id, kind="file", filename=filename, url=None,
            file_path=file_path, parse_state=ParseState.PARSING, quality="ok",
            parsed_text="", uploaded_at=_now(),
        )

    @classmethod
    def create_url(cls, project_id: int, url: str) -> IrSource:
        return cls(
            project_id=project_id, kind="url", filename=None, url=url,
            file_path=None, parse_state=ParseState.PARSING, quality="ok",
            parsed_text="", uploaded_at=_now(),
        )

    def display_name(self) -> str:
        return self.filename or self.url or f"source-{self.id}"


class IrChatMessage(Base):
    __tablename__ = "ir_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ir_projects.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    chapter_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_chapter_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(
        cls, project_id: int, role: str, content: str,
        chapter_id: int | None = None, updated_chapter_ids: list[int] | None = None,
    ) -> IrChatMessage:
        return cls(
            project_id=project_id, role=role, content=content,
            chapter_id=chapter_id, updated_chapter_ids=updated_chapter_ids or [],
            created_at=_now(),
        )


# ---------------- 纯函数 ----------------


def derive_project_status(chapters: list[IrChapter], queue_active: bool) -> str:
    if queue_active or any(
        c.state in (ChapterState.RESEARCHING, ChapterState.UPDATING) for c in chapters
    ):
        return "researching"
    if any(c.state == ChapterState.FAILED for c in chapters):
        return "partial_failed"
    if chapters and all(c.state in (ChapterState.DONE, ChapterState.STALE) for c in chapters):
        return "completed"
    return "draft"


def unresolved_tbds(content: dict) -> list[dict]:
    return [t for t in content.get("tbds", []) if not t.get("resolved")]


def resolve_tbd_in_content(content: dict, tbd_id: int, value: str) -> dict:
    """⟦tbd:id⟧ 原位替换为 value + 新 manual 引用标记；返回新 content（不改入参）。"""
    out = copy.deepcopy(content)
    tbd = next((t for t in out.get("tbds", []) if t.get("id") == tbd_id), None)
    if tbd is None or tbd.get("resolved"):
        raise ParamException(codes.IR_NOT_FOUND, "待补充项不存在或已处理")
    max_cite_id = max((c["id"] for c in out.get("citations", [])), default=0)
    cite = {
        "id": max_cite_id + 1,
        "n": len(out.get("citations", [])) + 1,
        "source_type": "manual",
        "title": "人工提供",
        "url": None,
        "source_id": None,
        "page": None,
        "quote": value,
        "captured_at": _now().strftime("%Y-%m"),
    }
    out.setdefault("citations", []).append(cite)
    marker = f"⟦tbd:{tbd_id}⟧"
    replaced = False
    for para in out.get("paragraphs", []):
        if marker in para["text"]:
            para["text"] = para["text"].replace(marker, f"{value}⟦c:{cite['id']}⟧")
            replaced = True
    if not replaced:
        # 正文标记已被人工删除：仅记录解决值
        out["citations"].pop()
    tbd["resolved"] = True
    tbd["value"] = value
    return out


def strip_markers(text: str) -> str:
    return _MARKER_RE.sub("", text)
