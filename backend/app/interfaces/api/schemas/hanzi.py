from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.domain.models.hanzi import HANZI_RE, clean_example_words

MAX_NAME_LEN = 64
MAX_DESC_LEN = 500
MAX_PINYIN_LEN = 32
MAX_AI_ADD_TEXT_LEN = 2000


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
    example_words: list[str] | None = None
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

    @field_validator("example_words")
    @classmethod
    def _v_words(cls, v: list[str] | None) -> list[str] | None:
        return clean_example_words(v)

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
    example_words: list[str] | None = None
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

    @field_validator("example_words")
    @classmethod
    def _v_words(cls, v: list[str] | None) -> list[str] | None:
        return clean_example_words(v)

    @field_validator("order_index")
    @classmethod
    def _v_order(cls, v: int | None) -> int | None:
        if v is None:
            return None
        if v < 0:
            raise ValueError("order_index 不能为负")
        return v


class AiAddRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def _v_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text 不能为空")
        if len(v) > MAX_AI_ADD_TEXT_LEN:
            raise ValueError(f"text 超过 {MAX_AI_ADD_TEXT_LEN} 字符")
        return v


class PracticeTextRequest(BaseModel):
    level_id: str

    @field_validator("level_id")
    @classmethod
    def _v_level_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("level_id 不能为空")
        return v
