"""文档解析器单测：docx/xlsx 真实小文件、扫描 PDF 走多模态、未知扩展报错。"""

from __future__ import annotations

import pytest

from app.domain.errors import ParamException, ServerException, codes
from app.infrastructure.ir_parsers import parse_document, parse_url


class FakeAgent:
    def __init__(self):
        self.image_calls: list[str] = []

    async def parse_image(self, image_bytes: bytes, hint: str) -> str:
        self.image_calls.append(hint)
        return "多模态解析出的文本"


@pytest.fixture
def agent() -> FakeAgent:
    return FakeAgent()


async def test_parse_docx_extracts_paragraphs_and_tables(tmp_path, agent):
    from docx import Document

    doc = Document()
    doc.add_paragraph("云帆科技商业计划书")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "2025 营收"
    table.rows[0].cells[1].text = "3.2 亿元"
    path = tmp_path / "bp.docx"
    doc.save(path)

    text, quality = await parse_document(path, agent)
    assert "云帆科技商业计划书" in text
    assert "3.2 亿元" in text
    assert quality == "ok"
    assert agent.image_calls == []


async def test_parse_xlsx_renders_sheets_as_csv(tmp_path, agent):
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "财务"
    ws.append(["年度", "营收"])
    ws.append([2025, 320000000])
    path = tmp_path / "fin.xlsx"
    wb.save(path)

    text, quality = await parse_document(path, agent)
    assert "财务" in text and "320000000" in text
    assert quality == "ok"


async def test_scanned_pdf_falls_back_to_multimodal_low_quality(tmp_path, agent):
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)  # 无文本层 = 扫描件
    path = tmp_path / "scan.pdf"
    with open(path, "wb") as f:
        writer.write(f)

    text, quality = await parse_document(path, agent)
    assert text == "多模态解析出的文本"
    assert quality == "low"
    assert len(agent.image_calls) == 1


async def test_image_goes_multimodal(tmp_path, agent):
    path = tmp_path / "shot.png"
    path.write_bytes(b"\x89PNG-fake")
    text, quality = await parse_document(path, agent)
    assert quality == "low" and text


async def test_unknown_extension_raises_2043(tmp_path, agent):
    path = tmp_path / "a.pptx"
    path.write_bytes(b"x")
    with pytest.raises(ParamException) as e:
        await parse_document(path, agent)
    assert e.value.code == codes.IR_SOURCE_UNPARSEABLE


async def test_parse_url_strips_tags(monkeypatch):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><head><script>x()</script><style>.a{}</style></head>"
                 "<body><h1>行业云报告</h1><p>市场规模 4562 亿元</p></body></html>",
        )

    import app.infrastructure.ir_parsers as mod
    monkeypatch.setattr(mod, "_url_transport", httpx.MockTransport(handler))
    text = await parse_url("https://example.com/report")
    assert "行业云报告" in text and "4562" in text
    assert "script" not in text and ".a{}" not in text


async def test_parse_url_failure_raises_upstream(monkeypatch):
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    import app.infrastructure.ir_parsers as mod
    monkeypatch.setattr(mod, "_url_transport", httpx.MockTransport(handler))
    with pytest.raises(ServerException) as e:
        await parse_url("https://example.com/x")
    assert e.value.code == codes.IR_UPSTREAM_FAILED
