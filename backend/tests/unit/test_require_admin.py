from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.dependencies import require_admin
from app.core.exceptions import AuthException
from app.models.user import User


def _user(role: str = "user") -> User:
    return User(
        id="u1",
        username="u",
        email="u@example.com",
        hashed_password="x",
        role=role,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_require_admin_allows_admin():
    db = AsyncMock()
    with patch("app.api.dependencies.UserRepo") as UserRepo:
        UserRepo.return_value.find_by_id = AsyncMock(return_value=_user("admin"))
        result = await require_admin(user_id="u1", db=db)
    assert result == "u1"


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    db = AsyncMock()
    with patch("app.api.dependencies.UserRepo") as UserRepo:
        UserRepo.return_value.find_by_id = AsyncMock(return_value=_user("user"))
        with pytest.raises(AuthException) as exc:
            await require_admin(user_id="u1", db=db)
    assert exc.value.code == 1002


@pytest.mark.asyncio
async def test_require_admin_rejects_missing_user():
    db = AsyncMock()
    with patch("app.api.dependencies.UserRepo") as UserRepo:
        UserRepo.return_value.find_by_id = AsyncMock(return_value=None)
        with pytest.raises(AuthException) as exc:
            await require_admin(user_id="u1", db=db)
    assert exc.value.code == 1002
