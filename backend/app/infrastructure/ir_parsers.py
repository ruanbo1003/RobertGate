"""invest-reports 文档/URL 解析器。

parse_document：按扩展名分发——
- .docx  python-docx 段落+表格全文
- .xlsx  openpyxl 逐 sheet 转「sheet 名 + CSV 行」
- .pdf   pypdf 逐页提取；全文 <50 字视为扫描件 → 多模态（quality=low）
- 图片   多模态（quality=low）
parse_url：httpx GET + 朴素去标签正文抽取。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import httpx

from app.application.ports import IrAgent
from app.domain.errors import ParamException, ServerException, codes

logger = logging.getLogger(__name__)

_SCANNED_PDF_MIN_CHARS = 50
_URL_TIMEOUT = 10.0
_url_transport: httpx.AsyncBaseTransport | None = None  # 测试注入


def _parse_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _parse_xlsx(path: Path) -> str:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    parts: list[str] = []
    for ws in wb.worksheets:
        parts.append(f"# sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = ["" if v is None else str(v) for v in row]
            if any(cells):
                parts.append(",".join(cells))
    wb.close()
    return "\n".join(parts)


def _parse_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


async def parse_document(path: Path, agent: IrAgent) -> tuple[str, str]:
    """返回 (text, quality)。quality: ok | low（多模态解析的扫描件/图片）。"""
    ext = path.suffix.lower()
    try:
        if ext == ".docx":
            return _parse_docx(path), "ok"
        if ext == ".xlsx":
            return _parse_xlsx(path), "ok"
        if ext == ".pdf":
            text = _parse_pdf_text(path)
            if len(text) >= _SCANNED_PDF_MIN_CHARS:
                return text, "ok"
            logger.info("PDF 文本层过少（%s 字），按扫描件走多模态：%s", len(text), path.name)
            return await agent.parse_image(path.read_bytes(), f"扫描版 PDF：{path.name}"), "low"
        if ext in (".png", ".jpg", ".jpeg"):
            return await agent.parse_image(path.read_bytes(), f"图片资料：{path.name}"), "low"
    except (ParamException, ServerException):
        raise
    except Exception as e:  # noqa: BLE001
        raise ParamException(
            codes.IR_SOURCE_UNPARSEABLE, f"文件解析失败：{path.name}（{e}）"
        ) from e
    raise ParamException(codes.IR_SOURCE_UNPARSEABLE, f"不支持的文件类型：{ext}")


_TAG_STRIP_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.IGNORECASE | re.DOTALL
)


async def parse_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            timeout=_URL_TIMEOUT, follow_redirects=True, transport=_url_transport,
            headers={"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                                    "Chrome/130.0 Safari/537.36")},
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as e:
        raise ServerException(codes.IR_UPSTREAM_FAILED, f"URL 抓取失败：{e}") from e
    if resp.status_code >= 400:
        raise ServerException(
            codes.IR_UPSTREAM_FAILED, f"URL 抓取失败 (HTTP {resp.status_code})"
        )
    text = _TAG_STRIP_RE.sub(" ", resp.text)
    return re.sub(r"\s+", " ", text).strip()
