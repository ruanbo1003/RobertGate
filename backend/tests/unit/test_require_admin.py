from datetime import datetime, timezone
import pytest

from app.application.services.auth_service import AuthService
from app.domain.errors import AuthException
from app.domain.models.user import User
from app.interfaces.api.deps import require_admin

from .conftest import make_uow


def _user(role: str = "user") -> User:
    return User(
        id="u1",
        username="u",
        email="u@example.com",
        hashed_password="x",
        role=role,
        created_at=datetime.now(timezone.utc),
    )


def _auth_service(find_by_id_return) -> AuthService:
    uow = make_uow()
    uow.users.find_by_id.return_value = find_by_id_return
    return AuthService(uow=uow)


# ---------- AuthService.ensure_admin ----------


@pytest.mark.asyncio
async def test_ensure_admin_allows_admin():
    auth = _auth_service(_user("admin"))
    await auth.ensure_admin("u1")  # 不抛异常即通过


@pytest.mark.asyncio
async def test_ensure_admin_rejects_regular_user():
    auth = _auth_service(_user("user"))
    with pytest.raises(AuthException) as exc:
        await auth.ensure_admin("u1")
    assert exc.value.code == 1002
    assert exc.value.message == "无权限"


@pytest.mark.asyncio
async def test_ensure_admin_rejects_missing_user():
    auth = _auth_service(None)
    with pytest.raises(AuthException) as exc:
        await auth.ensure_admin("u1")
    assert exc.value.code == 1002
    assert exc.value.message == "无权限"


# ---------- require_admin 依赖函数 ----------


@pytest.mark.asyncio
async def test_require_admin_allows_admin():
    auth = _auth_service(_user("admin"))
    result = await require_admin(user_id="u1", auth=auth)
    assert result == "u1"


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    auth = _auth_service(_user("user"))
    with pytest.raises(AuthException) as exc:
        await require_admin(user_id="u1", auth=auth)
    assert exc.value.code == 1002


@pytest.mark.asyncio
async def test_require_admin_rejects_missing_user():
    auth = _auth_service(None)
    with pytest.raises(AuthException) as exc:
        await require_admin(user_id="u1", auth=auth)
    assert exc.value.code == 1002
