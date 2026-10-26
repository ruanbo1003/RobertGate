"""DTO 时间序列化格式的行为锁。

改造前，出参里的时间一律走 service 私有的 `_iso()`：

    def _iso(dt): return dt.isoformat()

Python 的 `datetime.isoformat()` 对 UTC 时区给出 `+00:00` 后缀；而 Pydantic v2
默认的 JSON 序列化对同一个值给出 `Z` 后缀。DTO 化如果直接用裸 `datetime` 字段，
所有接口的时间字符串都会从 `+00:00` 悄悄变成 `Z`——前端按字符串比对/展示的地方
会跟着变。本文件把两件事钉死：

1. 默认行为确实不同（差异是真的，不是臆想出来的风险）；
2. `IsoDt` / `IsoDtOpt` 的序列化结果与 `isoformat()` 逐字节相等。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from app.application.dto.base import DTO, IsoDt, IsoDtOpt

# 现状实体里出现过的两类值：
#   - aware：所有 domain 工厂都用 datetime.now(timezone.utc)，也是线上 DB
#     （DateTime(timezone=True)）回读的形态；
#   - naive：单测直接构造实体时可能不带 tzinfo，也是 SQLite/历史数据的形态。
AWARE_UTC = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
AWARE_UTC_MICROS = datetime(2024, 1, 2, 3, 4, 5, 123456, tzinfo=timezone.utc)
AWARE_OFFSET = datetime(2024, 1, 2, 3, 4, 5, tzinfo=timezone(timedelta(hours=8)))
NAIVE = datetime(2024, 1, 2, 3, 4, 5)

ALL_CASES = [
    pytest.param(AWARE_UTC, id="aware-utc"),
    pytest.param(AWARE_UTC_MICROS, id="aware-utc-micros"),
    pytest.param(AWARE_OFFSET, id="aware-offset"),
    pytest.param(NAIVE, id="naive"),
]


def _iso_before_refactor(dt: datetime | None) -> str | None:
    """改造前三份 service 里那个 `_iso()` 的原样复制，作为对照基准。"""
    return dt.isoformat() if dt else None


class _PlainDatetimeModel(BaseModel):
    """反例：裸 datetime 字段，走 Pydantic 默认序列化。"""

    dt: datetime


class _IsoDtModel(DTO):
    dt: IsoDt
    dt_opt: IsoDtOpt = None


# ---------- 1. 默认行为与 _iso() 确实不同 ----------


def test_pydantic_default_diverges_from_isoformat_on_utc():
    """UTC aware：默认序列化给 `Z`，`_iso()` 给 `+00:00`——这就是本阶段的坑。"""
    dumped = _PlainDatetimeModel(dt=AWARE_UTC).model_dump(mode="json")["dt"]

    assert dumped == "2024-01-02T03:04:05Z"
    assert _iso_before_refactor(AWARE_UTC) == "2024-01-02T03:04:05+00:00"
    assert dumped != _iso_before_refactor(AWARE_UTC)


# ---------- 2. IsoDt 与 _iso() 逐字节相等 ----------


@pytest.mark.parametrize("value", ALL_CASES)
def test_isodt_serialization_matches_iso(value: datetime):
    model = _IsoDtModel(dt=value, dt_opt=value)
    expected = _iso_before_refactor(value)

    assert model.model_dump(mode="json")["dt"] == expected
    assert model.model_dump(mode="json")["dt_opt"] == expected
    # ApiResponse 走的就是 jsonable_encoder，这条才是真正上线的那条路径
    assert jsonable_encoder(model)["dt"] == expected
    assert jsonable_encoder(model)["dt_opt"] == expected


def test_isodtopt_keeps_none():
    model = _IsoDtModel(dt=AWARE_UTC, dt_opt=None)

    assert model.model_dump(mode="json")["dt_opt"] is None
    assert jsonable_encoder(model)["dt_opt"] is None
    assert _iso_before_refactor(None) is None


def test_utc_iso_string_has_offset_suffix_not_z():
    """兜底断言：出参里的 UTC 时间字符串必须以 `+00:00` 结尾。"""
    encoded = jsonable_encoder(_IsoDtModel(dt=AWARE_UTC))["dt"]

    assert encoded.endswith("+00:00")
    assert not encoded.endswith("Z")


def test_dto_reads_from_attributes():
    """DTO 基类开了 from_attributes，才能直接 model_validate(实体)。"""

    class _Entity:
        dt = AWARE_UTC
        dt_opt = None

    model = _IsoDtModel.model_validate(_Entity())

    assert jsonable_encoder(model)["dt"] == _iso_before_refactor(AWARE_UTC)
