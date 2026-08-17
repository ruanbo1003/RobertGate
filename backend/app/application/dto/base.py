"""DTO 基座：出参模型的公共基类与时间序列化约定。

`IsoDt` / `IsoDtOpt` 存在的唯一理由是格式保真：Pydantic v2 默认把 UTC 时间
序列化成 `...Z`，而改造前 service 里的 `_iso` 辅助函数用的是 `datetime.isoformat`
（UTC 是 `...+00:00`）。裸 `datetime` 字段会静默改变所有接口的时间字符串，
因此这里用 PlainSerializer 把格式钉回 `isoformat()`。
见 tests/unit/test_dto_datetime_format.py。
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, PlainSerializer

IsoDt = Annotated[
    datetime,
    PlainSerializer(lambda dt: dt.isoformat(), return_type=str),
]
IsoDtOpt = Annotated[
    datetime | None,
    PlainSerializer(
        lambda dt: dt.isoformat() if dt is not None else None, return_type=str | None
    ),
]


class DTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _Unset:
    """PATCH 语义哨兵的类型：区分"字段没传"与"字段传了 null"。"""

    def __repr__(self) -> str:  # pragma: no cover - 仅调试可读性
        return "UNSET"


UNSET: Any = _Unset()
