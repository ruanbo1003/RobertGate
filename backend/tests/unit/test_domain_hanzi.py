"""汉字领域模型测试：汉字抽取、例词清洗、实体工厂。"""

import pytest

from app.domain.models.hanzi import (
    HANZI_RE,
    MAX_EXAMPLE_WORD_LEN,
    MAX_EXAMPLE_WORDS,
    HanziCharacter,
    HanziLevel,
    HanziUserProgress,
    clean_example_words,
    extract_hanzi,
)
from app.domain.models.user import User


# ---------- extract_hanzi ----------


def test_extract_hanzi_dedup_ordered():
    assert extract_hanzi("你好世界，Hello 好！") == ["你", "好", "世", "界"]


def test_extract_hanzi_empty():
    assert extract_hanzi("no chinese here 123") == []


def test_hanzi_re_matches_single_char_only():
    assert HANZI_RE.match("人")
    assert not HANZI_RE.match("人口")
    assert not HANZI_RE.match("A")


# ---------- clean_example_words ----------


def test_clean_example_words_none_passthrough():
    assert clean_example_words(None) is None


def test_clean_example_words_strips_and_drops_empty():
    assert clean_example_words(["  人类  ", "", "  "]) == ["人类"]


def test_clean_example_words_rejects_non_string():
    with pytest.raises(ValueError, match="每项必须是字符串"):
        clean_example_words([123])  # type: ignore[list-item]


def test_clean_example_words_rejects_too_long_item():
    with pytest.raises(ValueError, match=f"单项超过 {MAX_EXAMPLE_WORD_LEN} 字符"):
        clean_example_words(["a" * (MAX_EXAMPLE_WORD_LEN + 1)])


def test_clean_example_words_rejects_too_many():
    with pytest.raises(ValueError, match=f"上限 {MAX_EXAMPLE_WORDS} 条"):
        clean_example_words([f"w{i}" for i in range(MAX_EXAMPLE_WORDS + 1)])


# ---------- 实体工厂 ----------


def test_level_new_fills_uuid_and_timestamps():
    level = HanziLevel.new("启蒙", "基础", 3)
    assert level.id
    assert level.name == "启蒙"
    assert level.order_index == 3
    assert level.created_at == level.updated_at


def test_level_touch_moves_updated_at_only():
    level = HanziLevel.new("启蒙", None, 0)
    created = level.created_at
    level.touch()
    assert level.created_at == created
    assert level.updated_at >= created


def test_character_new_defaults_example_words_to_list():
    c = HanziCharacter.new("l1", "人", "rén", None, 5)
    assert c.example_words == []
    assert c.order_index == 5
    assert c.level_id == "l1"


def test_character_new_keeps_example_words():
    c = HanziCharacter.new("l1", "人", "rén", ["人口"], 0)
    assert c.example_words == ["人口"]


def test_progress_new_sets_learned_at():
    p = HanziUserProgress.new("u1", "c1")
    assert p.id
    assert p.user_id == "u1"
    assert p.character_id == "c1"
    assert p.learned_at is not None


# ---------- User.is_admin ----------


def test_user_is_admin():
    assert User(role="admin").is_admin is True
    assert User(role="user").is_admin is False
