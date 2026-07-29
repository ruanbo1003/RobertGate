from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

HANZI_RE = re.compile(r"^[\u4e00-\u9fa5]$")

MAX_NAME_LEN = 64
MAX_DESC_LEN = 500
MAX_PINYIN_LEN = 32
MAX_MEANING_LEN = 500
BATCH_MAX = 200


def _strip_or_none(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v if v else None


# ---------- User side ----------


class UpdateProgressRequest(BaseModel):
    learned: bool


# ---------- Admin: Level ----------


class LevelCreateRequest(BaseModel):
    name: str
    description: str | None = None
    order_index: int = 0

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name 不能为空")
        if len(v) > MAX_NAME_LEN:
            raise ValueError(f"name 超过 {MAX_NAME_LEN} 字符")
        return v

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > MAX_DESC_LEN:
            raise ValueError(f"description 超过 {MAX_DESC_LEN} 字符")
        return v

    @field_validator("order_index")
    @classmethod
    def _v_order(cls, v: int) -> int:
        if v < 0:
            raise ValueError("order_index 不能为负")
        return v


class LevelUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    order_index: int | None = None

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("name 不能为空")
        if len(v) > MAX_NAME_LEN:
            raise ValueError(f"name 超过 {MAX_NAME_LEN} 字符")
        return v

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > MAX_DESC_LEN:
            raise ValueError(f"description 超过 {MAX_DESC_LEN} 字符")
        return v

    @field_validator("order_index")
    @classmethod
    def _v_order(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("order_index 不能为负")
        return v


# ---------- Admin: Character ----------


class CharacterCreateRequest(BaseModel):
    char: str
    pinyin: str
    meaning: str | None = None
    order_index: int | None = None

    @field_validator("char")
    @classmethod
    def _v_char(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("char 不能为空")
        if not HANZI_RE.match(v):
            raise ValueError("char 必须为单个汉字")
        return v

    @field_validator("pinyin")
    @classmethod
    def _v_pinyin(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("pinyin 不能为空")
        if len(v) > MAX_PINYIN_LEN:
            raise ValueError(f"pinyin 超过 {MAX_PINYIN_LEN} 字符")
        return v

    @field_validator("meaning")
    @classmethod
    def _v_meaning(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > MAX_MEANING_LEN:
            raise ValueError(f"meaning 超过 {MAX_MEANING_LEN} 字符")
        return v

    @field_validator("order_index")
    @classmethod
    def _v_order(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("order_index 不能为负")
        return v


class CharacterUpdateRequest(BaseModel):
    char: str | None = None
    pinyin: str | None = None
    meaning: str | None = None
    order_index: int | None = None

    @field_validator("char")
    @classmethod
    def _v_char(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("char 不能为空")
        if not HANZI_RE.match(v):
            raise ValueError("char 必须为单个汉字")
        return v

    @field_validator("pinyin")
    @classmethod
    def _v_pinyin(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("pinyin 不能为空")
        if len(v) > MAX_PINYIN_LEN:
            raise ValueError(f"pinyin 超过 {MAX_PINYIN_LEN} 字符")
        return v

    @field_validator("meaning")
    @classmethod
    def _v_meaning(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) > MAX_MEANING_LEN:
            raise ValueError(f"meaning 超过 {MAX_MEANING_LEN} 字符")
        return v

    @field_validator("order_index")
    @classmethod
    def _v_order(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("order_index 不能为负")
        return v


class BatchImportItem(BaseModel):
    char: str
    pinyin: str
    meaning: str | None = None


class BatchImportRequest(BaseModel):
    items: list[BatchImportItem] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def _v_items(cls, v: list[BatchImportItem]) -> list[BatchImportItem]:
        if not v:
            raise ValueError("items 不能为空")
        if len(v) > BATCH_MAX:
            raise ValueError(f"items 单次上限 {BATCH_MAX} 条")
        return v
