"""路由传输层契约测试：参数绑定位置（query vs form）这类 tsc 防不住的坑。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.ai.ir_agent_factory import set_ir_agent
from app.infrastructure.ai.ir_agent_mock import MockIrAgent
from app.main import app


@pytest.fixture
def client():
    set_ir_agent(MockIrAgent())
    from app.interfaces.api.deps import get_current_user_id

    app.dependency_overrides[get_current_user_id] = lambda: "u1"
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_user_id, None)
    set_ir_agent(None)


def test_upload_samples_accepts_type_as_multipart_form_field(client):
    """契约：type 随 multipart form 发送（docs/api §2.2 + 前端 investReports.ts）。"""
    resp = client.post(
        "/api/v1/invest-reports/samples",
        data={"type": "advice"},
        files=[("files", ("x.pdf", b"not-docx", "application/pdf"))],
    )
    body = resp.json()
    # 走到了业务校验（后缀不对 → 2040），而不是 FastAPI 的 422 缺参
    assert resp.status_code == 200, body
    assert body["code"] == 2040
