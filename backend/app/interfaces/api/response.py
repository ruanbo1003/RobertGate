from __future__ import annotations

from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


class ApiResponse(JSONResponse):
    """统一响应信封。

    `data` 里现在装的是 application/dto 下的 Pydantic 模型（可能嵌在 dict /
    list 里），JSONResponse 自己的 json.dumps 处理不了，统一先过
    jsonable_encoder。时间字段的格式由 DTO 上的 IsoDt 决定，不是这里。
    """

    def __init__(
        self,
        code: int = 0,
        data: Any = None,
        message: str = "ok",
        status_code: int = 200,
    ) -> None:
        content = {"code": code, "data": jsonable_encoder(data), "message": message}
        super().__init__(content=content, status_code=status_code)


def success(data: Any = None, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, data=data, message=message)


def error(code: int, message: str) -> ApiResponse:
    return ApiResponse(code=code, message=message)
