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
