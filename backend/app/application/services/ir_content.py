"""章节内容纯函数：Agent 局部编号草稿 → 全局 id 的 content JSON。"""

from __future__ import annotations

import logging
import re
from typing import Callable

from app.application.dto.invest_report import ChapterDraft

logger = logging.getLogger(__name__)

_LOCAL_MARKER_RE = re.compile(r"⟦(c|tbd):(\d+)⟧")


def remap_draft(draft: ChapterDraft, id_alloc: Callable[[], int]) -> dict:
    """把 ⟦c:N⟧/⟦tbd:N⟧ 局部序号重映射为全局 id；越界/未知标记移除并记 warning。"""
    cite_ids = [id_alloc() for _ in draft.citations]
    tbd_ids = [id_alloc() for _ in draft.tbds]

    def sub(m: re.Match) -> str:
        kind, n = m.group(1), int(m.group(2))
        ids = cite_ids if kind == "c" else tbd_ids
        if 1 <= n <= len(ids):
            return f"⟦{kind}:{ids[n - 1]}⟧"
        logger.warning("remap_draft: 丢弃越界标记 ⟦%s:%s⟧", kind, n)
        return ""

    paragraphs = [
        {"id": f"p{i + 1}", "text": _LOCAL_MARKER_RE.sub(sub, text)}
        for i, text in enumerate(draft.paragraphs)
    ]
    citations = [
        {
            "id": cite_ids[i],
            "n": i + 1,
            "source_type": c.source_type,
            "title": c.title,
            "url": c.url,
            "source_id": c.source_id,
            "page": c.page,
            "quote": c.quote,
            "captured_at": c.captured_at,
        }
        for i, c in enumerate(draft.citations)
    ]
    tbds = [
        {"id": tbd_ids[i], "reason": t.reason, "value": None, "resolved": False}
        for i, t in enumerate(draft.tbds)
    ]
    return {"paragraphs": paragraphs, "citations": citations, "tbds": tbds}
