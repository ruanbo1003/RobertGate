"""PatchModel.value_or_unset 的字段名守卫。

修复前：拼错字段名（如 `discription`）会静默走 `else UNSET` 分支，
调用方永远拿不到值也不会报错。修复后：非法字段名直接抛 AttributeError，
在开发期就能发现拼写错误。
"""

from __future__ import annotations

import pytest

from app.application.dto.base import UNSET
from app.interfaces.api.schemas._patch import PatchModel


class _Sample(PatchModel):
    name: str | None = None


def test_value_or_unset_known_field_not_set():
    model = _Sample()
    assert model.value_or_unset("name") is UNSET


def test_value_or_unset_known_field_set():
    model = _Sample(name="x")
    assert model.value_or_unset("name") == "x"


def test_value_or_unset_unknown_field_raises():
    model = _Sample()
    with pytest.raises(AttributeError):
        model.value_or_unset("nam")
