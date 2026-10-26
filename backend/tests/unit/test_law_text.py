"""民法典文本解析：中文数字转换 + 按条切分。"""

from __future__ import annotations

import pytest

from app.infrastructure.legal.law_text import chinese_numeral_to_int, split_articles


class TestChineseNumeralToInt:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("一", 1),
            ("九", 9),
            ("十", 10),
            ("十一", 11),
            ("二十", 20),
            ("九十九", 99),
            ("一百", 100),
            ("一百零八", 108),
            ("四百六十九", 469),
            ("七百一十", 710),
            ("一千", 1000),
            ("一千零八十七", 1087),
            ("一千二百六十", 1260),
        ],
    )
    def test_converts_numerals(self, text: str, expected: int) -> None:
        assert chinese_numeral_to_int(text) == expected

    def test_accepts_ling_variant(self) -> None:
        assert chinese_numeral_to_int("一百〇八") == 108


SAMPLE = """\
第一编 总则
第一章 基本规定
第一条　为了保护民事主体的合法权益，调整民事关系，制定本法。
第二条　民法调整平等主体的自然人、法人和非法人组织之间的
人身关系和财产关系。
第二分编 合同
第七百一十条　承租人按照约定的方法使用租赁物，
依据本法第五百一十条的规定仍不能确定的，不承担赔偿责任。
第一千零八十七条　离婚时，夫妻的共同财产由双方协议处理。
"""


class TestSplitArticles:
    def test_extracts_all_articles_in_order(self) -> None:
        articles = split_articles(SAMPLE)
        assert [a.article_no for a in articles] == [1, 2, 710, 1087]

    def test_label_is_original_header(self) -> None:
        articles = split_articles(SAMPLE)
        assert articles[2].label == "第七百一十条"

    def test_content_joins_wrapped_lines(self) -> None:
        articles = split_articles(SAMPLE)
        assert articles[1].content == (
            "民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。"
        )

    def test_inline_article_reference_does_not_split(self) -> None:
        articles = split_articles(SAMPLE)
        a710 = articles[2]
        assert "第五百一十条" in a710.content
        assert all(a.article_no != 510 for a in articles)

    def test_chapter_headings_excluded_from_content(self) -> None:
        articles = split_articles(SAMPLE)
        assert "分编" not in articles[1].content
        assert "第一章" not in articles[0].content

    def test_duplicate_article_no_keeps_first(self) -> None:
        text = "第一条　正文内容甲。\n第一条　重复出现的正文乙。\n"
        articles = split_articles(text)
        assert len(articles) == 1
        assert articles[0].content == "正文内容甲。"

    def test_empty_text_returns_empty(self) -> None:
        assert split_articles("") == []
