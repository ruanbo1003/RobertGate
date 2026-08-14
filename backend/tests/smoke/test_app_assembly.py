"""装配层冒烟测试。

覆盖 app/main.py 的路由注册 + middleware 顺序 + 统一响应信封，
这是重构前唯一盯着"整个 app 能不能跑起来"的测试。

关键点：`TestClient(app)` 不进 `with` 块 —— starlette 的 lifespan 只在
`__enter__` 时执行，不进 context manager 就不会触发 wait_for_db /
run_migrations，因此这里不需要真实数据库。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.application.services.gallery_service import GalleryService
from app.interfaces.api.deps import (
    get_admin_hanzi_service,
    get_auth_service,
    get_current_user_id,
    get_english_service,
    get_gallery_service,
    get_hanzi_service,
    get_t2i_task_service,
    get_translate_service,
    require_admin,
)
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# a) 路由清单快照
# ---------------------------------------------------------------------------

# 由 `.venv/bin/python -c "from app.main import app; ..."` 打印实际路由后
# 人工核对写死。任何路由增删都会让这个测试炸掉——这是本测试的设计目的。
EXPECTED_ROUTES = {
    ("DELETE", "/api/v1/admin/hanzi/characters/{character_id}"),
    ("DELETE", "/api/v1/admin/hanzi/levels/{level_id}"),
    ("DELETE", "/api/v1/ai/t2i/images/{image_id}"),
    ("DELETE", "/api/v1/ai/t2i/templates/{template_id}"),
    ("GET", "/api/health"),
    ("GET", "/api/v1/admin/hanzi/levels"),
    ("GET", "/api/v1/admin/hanzi/levels/{level_id}/characters"),
    ("GET", "/api/v1/ai/t2i/images/{image_id}"),
    ("GET", "/api/v1/ai/t2i/tasks/{task_id}"),
    ("GET", "/api/v1/ai/t2i/templates"),
    ("GET", "/api/v1/ai/t2i/templates/{code}/tasks"),
    ("GET", "/api/v1/auth/check-email/{email}"),
    ("GET", "/api/v1/auth/check-username/{username}"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/english/themes"),
    ("GET", "/api/v1/gallery/photos"),
    ("GET", "/api/v1/hanzi/levels"),
    ("GET", "/api/v1/hanzi/levels/{level_id}/characters"),
    ("GET", "/docs"),
    ("GET", "/docs/oauth2-redirect"),
    ("GET", "/openapi.json"),
    ("GET", "/redoc"),
    ("HEAD", "/docs"),
    ("HEAD", "/docs/oauth2-redirect"),
    ("HEAD", "/openapi.json"),
    ("HEAD", "/redoc"),
    ("PATCH", "/api/v1/ai/t2i/images/{image_id}"),
    ("POST", "/api/v1/admin/hanzi/levels"),
    ("POST", "/api/v1/admin/hanzi/levels/{level_id}/characters"),
    ("POST", "/api/v1/admin/hanzi/levels/{level_id}/characters/ai-add"),
    ("POST", "/api/v1/ai/grammar"),
    ("POST", "/api/v1/ai/native"),
    ("POST", "/api/v1/ai/t2i/tasks/{task_id}/retry"),
    ("POST", "/api/v1/ai/t2i/templates"),
    ("POST", "/api/v1/ai/t2i/templates/{code}/tasks"),
    ("POST", "/api/v1/ai/text-to-image"),
    ("POST", "/api/v1/ai/translate"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/english/quiz"),
    ("POST", "/api/v1/hanzi/practice-text"),
    ("PUT", "/api/v1/admin/hanzi/characters/{character_id}"),
    ("PUT", "/api/v1/admin/hanzi/levels/{level_id}"),
    ("PUT", "/api/v1/ai/t2i/templates/{template_id}"),
    ("PUT", "/api/v1/hanzi/progress/{character_id}"),
}


def test_route_inventory_matches_snapshot():
    actual = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set()) or set()
    }
    assert actual == EXPECTED_ROUTES


# ---------------------------------------------------------------------------
# b) 零 mock 行为链路：middleware 顺序 + 错误信封格式
# ---------------------------------------------------------------------------


def test_health_check_returns_envelope():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert "code" in body


def test_hanzi_levels_without_auth_returns_1001_envelope():
    response = client.get("/api/v1/hanzi/levels")
    assert response.status_code == 200
    assert response.json() == {"code": 1001, "data": None, "message": "未登录"}


def test_admin_hanzi_levels_without_token_returns_1001():
    response = client.get("/api/v1/admin/hanzi/levels")
    assert response.status_code == 200
    assert response.json()["code"] == 1001


def test_register_empty_body_returns_422():
    """锁定 FastAPI 默认 RequestValidationError 的对外形状（未被应用捕获转信封）。"""
    response = client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert isinstance(body["detail"], list)


# ---------------------------------------------------------------------------
# c) 7 个 router 各至少一条 200 路由
#
# 设计约束：provider 函数只从 app.api.dependencies 一个模块 import，
# 将来搬家时这个文件只用改 1 行 import。
# ---------------------------------------------------------------------------


def test_auth_router_smoke():
    mock_service = AsyncMock()
    mock_service.check_username.return_value = True
    app.dependency_overrides[get_auth_service] = lambda: mock_service

    response = client.get("/api/v1/auth/check-username/robert")

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_gallery_router_smoke():
    # 注入一个指向保证不存在路径的 GalleryService，避免依赖本机照片目录的
    # 真实状态（可能存在、可能不存在），同时避免测试意外在开发者本机目录里
    # 生成缩略图这种副作用。
    fake_photo_dir = Path("/nonexistent/robertgate-smoke-test-photo-dir")
    fake_service = GalleryService(
        photo_dir=fake_photo_dir,
        thumb_dir=fake_photo_dir / "thumbs",
        thumb_width=400,
    )
    app.dependency_overrides[get_gallery_service] = lambda: fake_service

    response = client.get("/api/v1/gallery/photos")

    assert response.status_code == 200
    assert response.json()["code"] in (5001, 5002)


def test_ai_tools_router_smoke_translate():
    mock_service = AsyncMock()
    mock_service.translate.return_value = {
        "source_lang": "en",
        "target_lang": "zh",
        "result": "你好",
    }
    app.dependency_overrides[get_translate_service] = lambda: mock_service

    response = client.post("/api/v1/ai/translate", json={"text": "hello"})

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_ai_tools_router_smoke_english_themes():
    # EnglishService 方法是同步的，router 里也没有 await，因此这里必须用
    # 同步 mock（MagicMock），用 AsyncMock 会把一个 coroutine 塞进 JSON body。
    mock_service = MagicMock()
    mock_service.list_themes.return_value = {"themes": []}
    app.dependency_overrides[get_english_service] = lambda: mock_service

    response = client.get("/api/v1/english/themes")

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_t2i_router_smoke():
    mock_service = AsyncMock()
    mock_service.list_templates.return_value = {"templates": []}
    app.dependency_overrides[get_t2i_task_service] = lambda: mock_service

    response = client.get("/api/v1/ai/t2i/templates")

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_hanzi_router_smoke():
    mock_service = AsyncMock()
    mock_service.list_levels_with_progress.return_value = {"levels": []}
    app.dependency_overrides[get_hanzi_service] = lambda: mock_service
    app.dependency_overrides[get_current_user_id] = lambda: "fake-user-id"

    response = client.get("/api/v1/hanzi/levels")

    assert response.status_code == 200
    assert response.json()["code"] == 0


def test_admin_hanzi_router_smoke():
    mock_service = AsyncMock()
    mock_service.list_levels.return_value = {"levels": []}
    app.dependency_overrides[get_admin_hanzi_service] = lambda: mock_service
    app.dependency_overrides[require_admin] = lambda: "fake-admin-id"

    response = client.get("/api/v1/admin/hanzi/levels")

    assert response.status_code == 200
    assert response.json()["code"] == 0


# util router（/api/health）已在 test_health_check_returns_envelope 中覆盖。
