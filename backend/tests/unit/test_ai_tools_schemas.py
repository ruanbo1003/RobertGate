import pytest
from pydantic import ValidationError

from app.schemas.ai_tools import (
    AddHanziRequest,
    CharacterInfoRequest,
    QuizRequest,
    SentenceRequest,
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


# --- Add Hanzi ---


def test_add_hanzi_ok():
    req = AddHanziRequest(text="汉字")
    assert req.text == "汉字"


def test_add_hanzi_empty():
    with pytest.raises(ValidationError):
        AddHanziRequest(text="")


def test_add_hanzi_too_long():
    with pytest.raises(ValidationError):
        AddHanziRequest(text="a" * 5001)


# --- Character Info ---


def test_character_info_ok():
    req = CharacterInfoRequest(char="汉")
    assert req.char == "汉"


def test_character_info_multi_char():
    with pytest.raises(ValidationError):
        CharacterInfoRequest(char="汉字")


def test_character_info_non_chinese():
    with pytest.raises(ValidationError):
        CharacterInfoRequest(char="A")


# --- Sentence ---


def test_sentence_ok():
    req = SentenceRequest(known_chars=["汉", "字", "是", "中", "华"])
    assert len(req.known_chars) == 5


def test_sentence_too_few():
    with pytest.raises(ValidationError):
        SentenceRequest(known_chars=["汉", "字"])


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
