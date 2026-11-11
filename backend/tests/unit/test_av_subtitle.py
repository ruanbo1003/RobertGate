"""对白镜字幕对齐纯函数单测（whisper 词级时间戳 -> 逐句字幕条目）。"""

from __future__ import annotations

from app.application.services.av_subtitle import align_dialogue


def test_align_dialogue_splits_on_word_boundaries_with_full_match():
    lines = ["Hello Lily", "Hi Max"]
    words = [
        ("Hello", 0.0, 0.5),
        ("Lily", 0.5, 1.0),
        ("Hi", 1.0, 1.3),
        ("Max", 1.3, 1.8),
    ]
    result = align_dialogue(lines, words, total=1.8)
    assert result == [
        ("Hello Lily", 0.0, 1.0),
        ("Hi Max", 1.0, 1.8),
    ]


def test_align_dialogue_empty_words_falls_back_to_even_split():
    lines = ["one", "two", "three"]
    result = align_dialogue(lines, [], total=9.0)
    assert len(result) == 3
    assert result == [("one", 0.0, 3.0), ("two", 3.0, 6.0), ("three", 6.0, 9.0)]


def test_align_dialogue_low_match_rate_falls_back_to_even_split():
    lines = ["Hello", "Lily is here"]
    # whisper 全部识别错（match rate 0）——应回退均分，而非贴着错误词边界切
    words = [
        ("xx", 0.0, 0.3),
        ("yy", 0.3, 1.0),
        ("zz", 1.0, 1.6),
        ("ww", 1.6, 2.0),
    ]
    result = align_dialogue(lines, words, total=2.0)
    assert result == [("Hello", 0.0, 1.0), ("Lily is here", 1.0, 2.0)]


def test_align_dialogue_over_recognition_does_not_raise():
    lines = ["Hi there"]
    words = [
        ("um", 0.0, 0.2),
        ("hi", 0.2, 0.5),
        ("there", 0.5, 0.9),
        ("extra", 0.9, 1.2),
    ]
    result = align_dialogue(lines, words, total=1.2)
    assert len(result) == 1


def test_align_dialogue_under_recognition_does_not_raise():
    lines = ["Hello Lily", "Hi Max"]
    # whisper 漏识别了一个词（只有 3 个词对应 4 个已知 token）
    words = [
        ("hello", 0.0, 0.5),
        ("hi", 0.5, 0.9),
        ("max", 0.9, 1.3),
    ]
    result = align_dialogue(lines, words, total=1.3)
    assert len(result) == 2


def test_align_dialogue_empty_lines_returns_empty_list():
    assert align_dialogue([], [("a", 0.0, 1.0)], total=1.0) == []
