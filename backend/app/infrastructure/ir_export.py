"""invest-reports Word 导出（python-docx）。

P0 降级（见实现计划 Task 8）：不还原范本完整样式，仅标题层级 + 基础字体；
传入段落须已 strip_markers，产出为干净稿。
"""

from __future__ import annotations

import io

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

_TYPE_LABEL = {"advice": "投资建议书", "dd": "尽调报告"}


def _set_cjk_font(doc: Document) -> None:
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def build_docx(project_title: str, report_type: str, chapters: list[dict]) -> bytes:
    doc = Document()
    _set_cjk_font(doc)
    doc.add_heading(project_title, level=0)
    doc.add_paragraph(_TYPE_LABEL.get(report_type, report_type))
    for chapter in chapters:
        doc.add_heading(chapter["title"], level=1)
        for text in chapter["paragraphs"]:
            if text.strip():
                doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
