"""对白镜字幕对齐纯函数：whisper 词级时间戳 -> 每句台词的 (text, start, end)。

已知台词是真值（内容绝对准确，来自剧本），whisper 只用来估时间。贪心按词序
消费，用匹配率守门：对不上就整体放弃、按台词长度均分镜时长，字幕永不缺条目。
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r"[A-Za-z0-9']+|[一-鿿]")
_MATCH_RATE_MIN = 0.5


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


def _norm_word(word: str) -> str:
    return "".join(_TOKEN_RE.findall(word.lower()))


def _even_split(lines: list[str], total: float) -> list[tuple[str, float, float]]:
    n = len(lines)
    step = total / n
    return [(line, round(i * step, 2), round((i + 1) * step, 2)) for i, line in enumerate(lines)]


def align_dialogue(
    lines: list[str], words: list[tuple[str, float, float]], total: float
) -> list[tuple[str, float, float]]:
    if not lines:
        return []
    if not words:
        return _even_split(lines, total)

    line_tokens = [_tokenize(line) for line in lines]
    total_tokens = sum(len(t) for t in line_tokens)
    if total_tokens == 0:
        return _even_split(lines, total)

    segments: list[tuple[str, float, float]] = []
    widx = 0
    matched = 0
    for line, tokens in zip(lines, line_tokens):
        k = len(tokens)
        if k == 0 or widx >= len(words):
            start = segments[-1][2] if segments else 0.0
            segments.append((line, start, start))
            continue
        take = min(k, len(words) - widx)
        start = words[widx][1]
        end = words[widx + take - 1][2]
        for i in range(take):
            if _norm_word(words[widx + i][0]) == tokens[i]:
                matched += 1
        widx += take
        segments.append((line, start, end))

    if matched / total_tokens < _MATCH_RATE_MIN:
        return _even_split(lines, total)

    last_text, last_start, _ = segments[-1]
    segments[-1] = (last_text, last_start, total)
    return segments
