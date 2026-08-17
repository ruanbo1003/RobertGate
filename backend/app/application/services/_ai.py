"""AI 调用的统一兜底。

原来每个 AI 调用点都手写一遍 try/except，错误码与文案各不相同；这里收成
一个 helper，**文案由调用方逐字给全**（含分隔符——历史上有的用半角
`": "`，有的用全角 `"："`，不能统一）。
"""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

from app.domain.errors import AppException, ServerException, codes

T = TypeVar("T")


async def ai_call(
    awaitable: Awaitable[T],
    *,
    code: int = codes.AI_UNAVAILABLE,
    message: str = "AI 服务不可用",
    sep: str = ": ",
    exc: type[AppException] = ServerException,
) -> T:
    try:
        return await awaitable
    except AppException:
        raise
    except Exception as e:
        raise exc(code, f"{message}{sep}{e}") from e
