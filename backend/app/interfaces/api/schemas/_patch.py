"""PATCH/PUT 局部更新请求的公共基类。

可空字段有两种"没值"：请求体里根本没这个 key（保持不变），和显式传了
`null`（清空）。Pydantic 把两者都还原成 `None`，只有 `model_fields_set`
分得清。以前靠 router 额外传一个 `xxx_set: bool` 给 service，一个字段两个
参数；现在统一由 `value_or_unset()` 折成一个值，service 判 `is not UNSET`。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.application.dto.base import UNSET


class PatchModel(BaseModel):
    def value_or_unset(self, field: str) -> Any:
        return getattr(self, field) if field in self.model_fields_set else UNSET
