import pytest
from pydantic import ValidationError

from app.schemas.hanzi import (
    AiAddRequest,
    CharacterCreateRequest,
    CharacterUpdateRequest,
    LevelCreateRequest,
    LevelUpdateRequest,
    UpdateProgressRequest,
)


# ---------- UpdateProgressRequest ----------


def test_update_progress_ok():
    req = UpdateProgressRequest(learned=True)
    assert req.learned is True


def test_update_progress_missing_learned():
    with pytest.raises(ValidationError):
        UpdateProgressRequest()  # type: ignore[call-arg]


# ---------- LevelCreateRequest ----------


def test_level_create_ok():
    req = LevelCreateRequest(name="启蒙 Level 1", description="基础", order_index=1)
    assert req.name == "启蒙 Level 1"
    assert req.order_index == 1


def test_level_create_empty_name():
    with pytest.raises(ValidationError):
        LevelCreateRequest(name="   ", order_index=0)


def test_level_create_name_too_long():
    with pytest.raises(ValidationError):
        LevelCreateRequest(name="a" * 65, order_index=0)


def test_level_create_description_too_long():
    with pytest.raises(ValidationError):
        LevelCreateRequest(name="x", description="d" * 501, order_index=0)


def test_level_create_negative_order():
    with pytest.raises(ValidationError):
        LevelCreateRequest(name="x", order_index=-1)


# ---------- LevelUpdateRequest ----------


def test_level_update_partial():
    req = LevelUpdateRequest(name="new")
    assert req.name == "new"
    assert req.description is None
    assert req.order_index is None


def test_level_update_all_none():
    req = LevelUpdateRequest()
    assert req.name is None


# ---------- CharacterCreateRequest ----------


def test_char_create_ok():
    req = CharacterCreateRequest(
        char="人", pinyin="rén", example_words=["人类", "人口"]
    )
    assert req.char == "人"
    assert req.example_words == ["人类", "人口"]


def test_char_create_non_hanzi():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(char="A", pinyin="a")


def test_char_create_multi():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(char="人口", pinyin="rén kǒu")


def test_char_create_empty_pinyin():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(char="人", pinyin="  ")


def test_char_create_pinyin_too_long():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(char="人", pinyin="a" * 33)


def test_char_create_example_word_too_long():
    with pytest.raises(ValidationError):
        CharacterCreateRequest(
            char="人", pinyin="rén", example_words=["a" * 17]
        )


def test_char_create_example_words_strip_empty():
    req = CharacterCreateRequest(
        char="人", pinyin="rén", example_words=["  人类  ", "", "  "]
    )
    assert req.example_words == ["人类"]


# ---------- CharacterUpdateRequest ----------


def test_char_update_partial():
    req = CharacterUpdateRequest(pinyin="rén")
    assert req.pinyin == "rén"
    assert req.char is None


def test_char_update_example_words_omitted():
    req = CharacterUpdateRequest(pinyin="rén")
    assert req.example_words is None
    assert "example_words" not in req.model_fields_set


def test_char_update_example_words_explicit_empty():
    req = CharacterUpdateRequest(example_words=[])
    assert req.example_words == []
    assert "example_words" in req.model_fields_set


# ---------- AiAddRequest ----------


def test_ai_add_ok():
    req = AiAddRequest(text="你好世界")
    assert req.text == "你好世界"


def test_ai_add_empty():
    with pytest.raises(ValidationError):
        AiAddRequest(text="   ")


def test_ai_add_too_long():
    with pytest.raises(ValidationError):
        AiAddRequest(text="字" * 2001)
