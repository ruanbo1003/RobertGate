from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


class ApiResponse(JSONResponse):
    def __init__(
        self,
        code: int = 0,
        data: Any = None,
        message: str = "ok",
        status_code: int = 200,
    ) -> None:
        content = {"code": code, "data": data, "message": message}
        super().__init__(content=content, status_code=status_code)


def success(data: Any = None, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, data=data, message=message)


def error(code: int, message: str) -> ApiResponse:
    return ApiResponse(code=code, message=message)
