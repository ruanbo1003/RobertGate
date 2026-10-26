"""民法典文本解析：中文数字转换 + 按"条"切分。

法条正文里存在"依据本法第五百一十条的规定"这类行内引用，
因此条文头只认**行首**的"第 X 条"；编/章/节/分编标题行直接丢弃。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}
_UNITS = {"十": 10, "百": 100, "千": 1000}

_NUMERAL = "零〇一二三四五六七八九十百千"
_ARTICLE_RE = re.compile(rf"^(第([{_NUMERAL}]+)条)")
_STRUCT_RE = re.compile(rf"^第[{_NUMERAL}]+(?:分编|编|章|节)")


def chinese_numeral_to_int(text: str) -> int:
    """把"一千零八十七"这类中文数字转成 int。"""
    total = 0
    digit = 0
    for ch in text:
        if ch in _DIGITS:
            digit = _DIGITS[ch]
        elif ch in _UNITS:
            unit = _UNITS[ch]
            if digit == 0:
                digit = 1
            total += digit * unit
            digit = 0
    return total + digit


@dataclass(frozen=True)
class ParsedArticle:
    article_no: int
    label: str
    content: str


def split_articles(text: str) -> list[ParsedArticle]:
    """按行首"第 X 条"切分全文，返回按出现顺序排列的条文列表。

    - 换行折断的正文重新拼接；
    - 编/章/节/分编标题行不计入任何条文内容；
    - 重复出现的条号只保留第一次（防目录等噪声）。
    """
    articles: list[ParsedArticle] = []
    seen: set[int] = set()
    current_no: int | None = None
    current_label = ""
    current_parts: list[str] = []

    def flush() -> None:
        nonlocal current_no
        if current_no is None:
            return
        if current_no not in seen:
            seen.add(current_no)
            articles.append(
                ParsedArticle(
                    article_no=current_no,
                    label=current_label,
                    content="".join(current_parts),
                )
            )
        current_no = None

    for line in text.splitlines():
        stripped = line.strip().strip("　")
        if not stripped:
            continue
        m = _ARTICLE_RE.match(stripped)
        if m:
            flush()
            current_no = chinese_numeral_to_int(m.group(2))
            current_label = m.group(1)
            current_parts = []
            rest = stripped[m.end() :].strip().strip("　")
            if rest:
                current_parts.append(rest)
            continue
        if _STRUCT_RE.match(stripped):
            continue
        if current_no is not None:
            current_parts.append(stripped)

    flush()
    return articles
