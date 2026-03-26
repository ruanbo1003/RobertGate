from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 0
    data: Any = None
    message: str = "ok"


def success(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


def error(code: int, message: str) -> dict:
    return {"code": code, "data": None, "message": message}
