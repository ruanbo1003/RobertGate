"""法律咨询请求 Schema。"""

from __future__ import annotations

from pydantic import BaseModel


class SendMessageRequest(BaseModel):
    content: str
