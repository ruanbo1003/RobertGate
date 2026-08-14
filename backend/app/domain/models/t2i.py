from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.errors import ParamException, codes
from app.domain.models.base import Base

ITEM_MAX_LENGTH = 100
CODE_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
ITEM_PLACEHOLDER = "{{item}}"


class TaskStatus(StrEnum):
    """任务与图片共用的生成状态（值与 DB 里的历史字符串一致）。"""

    GENERATING = "generating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_keywords(raw: dict[str, Any]) -> dict[str, str]:
    """校验并规范化任务关键词。单变量 `item`。"""
    value = raw.get("item")
    if value is None:
        raise ParamException(codes.T2I_ITEM_INVALID, "item 不能为空")
    if not isinstance(value, str):
        raise ParamException(codes.T2I_ITEM_INVALID, "item 必须是字符串")
    value = value.strip()
    if not value:
        raise ParamException(codes.T2I_ITEM_INVALID, "item 不能为空")
    if len(value) > ITEM_MAX_LENGTH:
        raise ParamException(
            codes.T2I_ITEM_INVALID, f"item 超长（最大 {ITEM_MAX_LENGTH} 字符）"
        )
    return {"item": value}


def business_status(images: list[T2IImage]) -> str:
    """业务状态：只要有一张被标记为可用就算 done。"""
    return "done" if any(i.available for i in images) else "pending"


def _validate_name_and_prompt(name: str, prompt: str) -> None:
    if not name:
        raise ParamException(codes.T2I_TEMPLATE_NAME_INVALID, "name 不能为空")
    if len(name) > 64:
        raise ParamException(
            codes.T2I_TEMPLATE_NAME_INVALID, "name 超长（最大 64 字符）"
        )
    if not prompt:
        raise ParamException(codes.T2I_TEMPLATE_PROMPT_INVALID, "prompt 不能为空")
    if ITEM_PLACEHOLDER not in prompt:
        raise ParamException(
            codes.T2I_TEMPLATE_PROMPT_INVALID,
            f"prompt 必须包含占位符 {ITEM_PLACEHOLDER}",
        )


class T2ITemplate(Base):
    __tablename__ = "t2i_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    @classmethod
    def create(
        cls,
        code: str,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> T2ITemplate:
        code = (code or "").strip().lower()
        name = (name or "").strip()
        prompt = (prompt or "").strip()

        if not CODE_RE.match(code):
            raise ParamException(
                codes.T2I_TEMPLATE_CODE_INVALID,
                "code 只允许小写字母/数字/连字符，须以字母开头，长度 2-64",
            )
        _validate_name_and_prompt(name, prompt)

        now = _now()
        return cls(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=(description or None),
            prompt=prompt,
            order_index=order_index if order_index is not None else 0,
            is_builtin=False,
            created_at=now,
            updated_at=now,
        )

    def apply_update(
        self,
        name: str,
        description: str | None,
        prompt: str,
        order_index: int | None,
    ) -> None:
        name = (name or "").strip()
        prompt = (prompt or "").strip()
        _validate_name_and_prompt(name, prompt)

        self.name = name
        self.description = (description or "").strip() or None
        self.prompt = prompt
        if order_index is not None:
            self.order_index = order_index
        self.updated_at = _now()

    def ensure_editable(self) -> None:
        if self.is_builtin:
            raise ParamException(codes.T2I_TEMPLATE_BUILTIN, "内置模板不可修改")

    def ensure_deletable(self) -> None:
        if self.is_builtin:
            raise ParamException(codes.T2I_TEMPLATE_BUILTIN, "内置模板不可删除")

    def render_prompt(self, keywords: dict[str, str]) -> str:
        return self.prompt.replace(ITEM_PLACEHOLDER, keywords["item"])


class T2ITask(Base):
    __tablename__ = "t2i_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_code: Mapped[str] = mapped_column(String(32), index=True)
    keywords: Mapped[dict] = mapped_column(JSONB)
    keywords_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="generating")
    last_failed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @staticmethod
    def compute_hash(template_code: str, keywords: dict[str, str]) -> str:
        canonical = json.dumps(
            keywords, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        payload = f"{template_code}|{canonical}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @classmethod
    def create(cls, template_code: str, keywords: dict[str, str]) -> T2ITask:
        now = _now()
        return cls(
            id=str(uuid.uuid4()),
            template_code=template_code,
            keywords=keywords,
            keywords_hash=cls.compute_hash(template_code, keywords),
            status=TaskStatus.GENERATING,
            last_failed=False,
            created_at=now,
            updated_at=now,
        )

    def touch(self) -> None:
        self.updated_at = _now()

    def mark_generating(self) -> None:
        self.status = TaskStatus.GENERATING
        self.updated_at = _now()

    def mark_succeeded(self) -> None:
        self.status = TaskStatus.SUCCEEDED
        self.last_failed = False
        self.updated_at = _now()

    def mark_failed(self) -> None:
        self.status = TaskStatus.FAILED
        self.last_failed = True
        self.updated_at = _now()


class T2IImage(Base):
    __tablename__ = "t2i_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("t2i_tasks.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[str] = mapped_column(String(16), default="generating")
    available: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    @classmethod
    def create(cls, task_id: str) -> T2IImage:
        return cls(
            id=str(uuid.uuid4()),
            task_id=task_id,
            status=TaskStatus.GENERATING,
            available=False,
            mime=None,
            created_at=_now(),
        )

    def mark_succeeded(self, mime: str | None) -> None:
        self.status = TaskStatus.SUCCEEDED
        self.mime = mime

    def mark_failed(self) -> None:
        self.status = TaskStatus.FAILED

    def set_available(self, value: bool) -> None:
        if self.status != TaskStatus.SUCCEEDED:
            raise ParamException(
                codes.T2I_IMAGE_NOT_SUCCEEDED, "只有已生成的图片可以标记"
            )
        self.available = value

    def ensure_deletable(self) -> None:
        if self.available:
            raise ParamException(
                codes.T2I_IMAGE_IN_USE, "可用图片不可删除，请先取消可用"
            )


class T2IImageBlob(Base):
    __tablename__ = "t2i_image_blobs"

    image_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("t2i_images.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bytes_: Mapped[bytes] = mapped_column("bytes", LargeBinary)
