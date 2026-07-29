import pytest
from pydantic import ValidationError

from app.schemas.ai_tools import (
    QuizRequest,
    Text2ImageRequest,
    TranslateRequest,
)


# --- Translate ---


def test_translate_request_ok():
    req = TranslateRequest(text="hello", action="translate")
    assert req.action == "translate"


def test_translate_request_empty_text():
    with pytest.raises(ValidationError):
        TranslateRequest(text="   ", action="translate")


def test_translate_request_text_too_long():
    with pytest.raises(ValidationError):
        TranslateRequest(text="a" * 2001, action="translate")


def test_translate_request_invalid_action():
    with pytest.raises(ValidationError):
        TranslateRequest(text="hi", action="unknown")  # type: ignore[arg-type]


# --- Quiz ---


def test_quiz_ok():
    req = QuizRequest(theme_id="colors")
    assert req.count == 10


# --- Text2Image ---


def test_t2i_ok():
    req = Text2ImageRequest(prompt="a cat")
    assert req.size == "1024x1024"


def test_t2i_empty_prompt():
    with pytest.raises(ValidationError):
        Text2ImageRequest(prompt="   ")


def test_t2i_prompt_too_long():
    with pytest.raises(ValidationError):
        Text2ImageRequest(prompt="a" * 1001)


def test_t2i_bad_size():
    with pytest.raises(ValidationError):
        Text2ImageRequest(prompt="cat", size="512x512")
