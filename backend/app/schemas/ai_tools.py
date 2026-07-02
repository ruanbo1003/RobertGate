from typing import Literal

from pydantic import BaseModel, Field, field_validator


# --- Translate ---

TranslateAction = Literal["translate", "grammar", "native"]


class TranslateRequest(BaseModel):
    text: str
    action: TranslateAction

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text 不能为空")
        if len(v) > 2000:
            raise ValueError("text 超过 2000 字符")
        return v


# --- Hanzi ---

class AddHanziRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text 不能为空")
        if len(v) > 5000:
            raise ValueError("text 超过 5000 字符")
        return v


class UpdateHanziRequest(BaseModel):
    learned: bool


class CharacterInfoRequest(BaseModel):
    char: str

    @field_validator("char")
    @classmethod
    def validate_char(cls, v: str) -> str:
        if not v:
            raise ValueError("char 不能为空")
        if len(v) != 1 or not ("\u4e00" <= v <= "\u9fff"):
            raise ValueError("char 必须为单个汉字")
        return v


class SentenceRequest(BaseModel):
    known_chars: list[str] = Field(default_factory=list)

    @field_validator("known_chars")
    @classmethod
    def validate_chars(cls, v: list[str]) -> list[str]:
        if len(v) == 0:
            raise ValueError("known_chars 不能为空")
        if len(v) < 5:
            raise ValueError("known_chars 少于 5 个字")
        return v


# --- English ---

class QuizRequest(BaseModel):
    theme_id: str
    count: int = 10

    @field_validator("theme_id")
    @classmethod
    def validate_theme_id(cls, v: str) -> str:
        if not v:
            raise ValueError("theme_id 不能为空")
        return v


# --- Text2Image ---

class Text2ImageRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt 不能为空")
        if len(v) > 1000:
            raise ValueError("prompt 超过 1000 字符")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: str) -> str:
        if v != "1024x1024":
            raise ValueError("size 不支持")
        return v
