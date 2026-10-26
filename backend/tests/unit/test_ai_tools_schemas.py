import pytest
from pydantic import ValidationError

from app.interfaces.api.schemas.ai_tools import (
    QuizRequest,
    Text2ImageRequest,
    TextRequest,
)


# --- Translate / Grammar / Native (共用 TextRequest) ---


def test_text_request_ok():
    req = TextRequest(text="hello")
    assert req.text == "hello"


def test_text_request_empty_text():
    with pytest.raises(ValidationError):
        TextRequest(text="   ")


def test_text_request_too_long():
    with pytest.raises(ValidationError):
        TextRequest(text="a" * 2001)


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
