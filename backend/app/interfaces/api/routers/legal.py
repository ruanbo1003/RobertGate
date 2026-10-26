"""法律咨询路由。

发送消息走 SSE 流式（citations → delta → done / error）；
参数校验失败与未登录在建流之前就以统一 JSON 信封返回（由中间件转换）。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from app.application.services.legal_service import LegalConsultService
from app.interfaces.api.deps import get_current_user_id, get_legal_service
from app.interfaces.api.response import success
from app.interfaces.api.schemas.legal import SendMessageRequest

router = APIRouter(prefix="/legal-consult", tags=["legal-consult"])


def sse_frame(event: str, payload: dict) -> str:
    data = json.dumps(jsonable_encoder(payload), ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


async def _sse_stream(
    service: LegalConsultService, user_id: str, content: str
) -> AsyncIterator[str]:
    async for event, payload in service.stream_reply(user_id, content):
        yield sse_frame(event, payload)


@router.post("/messages")
async def send_message(
    body: SendMessageRequest,
    user_id: str = Depends(get_current_user_id),
    service: LegalConsultService = Depends(get_legal_service),
):
    content = service.validate_content(body.content)
    return StreamingResponse(
        _sse_stream(service, user_id, content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/messages")
async def list_messages(
    user_id: str = Depends(get_current_user_id),
    service: LegalConsultService = Depends(get_legal_service),
):
    data = await service.list_messages(user_id)
    return success(data)


@router.delete("/messages")
async def clear_messages(
    user_id: str = Depends(get_current_user_id),
    service: LegalConsultService = Depends(get_legal_service),
):
    await service.clear_messages(user_id)
    return success(None)


@router.get("/articles/{article_no}")
async def get_article(
    article_no: int,
    user_id: str = Depends(get_current_user_id),
    service: LegalConsultService = Depends(get_legal_service),
):
    data = await service.get_article(article_no)
    return success(data)
