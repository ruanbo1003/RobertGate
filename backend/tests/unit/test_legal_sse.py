"""SSE 帧格式化：event + data 两行一帧，中文不转义，DTO 可序列化。"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.application.dto.legal import CitationDTO, LegalMessageDTO
from app.interfaces.api.routers.legal import sse_frame


class TestSseFrame:
    def test_formats_event_and_data(self) -> None:
        frame = sse_frame("delta", {"text": "你好"})
        assert frame == 'event: delta\ndata: {"text": "你好"}\n\n'

    def test_serializes_dto_payload(self) -> None:
        dto = LegalMessageDTO(
            id="m-1",
            role="assistant",
            content="回答",
            citations=[CitationDTO(article_no=710, label="第七百一十条")],
            created_at=datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc),
        )
        frame = sse_frame("done", {"message": dto})
        payload = json.loads(frame.split("data: ", 1)[1].strip())
        assert payload["message"]["citations"][0]["article_no"] == 710
        assert payload["message"]["created_at"] == "2026-10-24T10:00:00+00:00"
