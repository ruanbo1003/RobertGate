from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AuthException
from app.models.password_reset import PasswordReset
from app.models.user import User
from app.service.auth_service import AuthService


@pytest.fixture
def user_repo():
    return AsyncMock()


@pytest.fixture
def reset_repo():
    return AsyncMock()


@pytest.fixture
def auth_service(user_repo, reset_repo):
    return AuthService(user_repo=user_repo, reset_repo=reset_repo)


def _make_user(username="testuser", email="test@example.com", password="pass1234"):
    import uuid
    from datetime import datetime, timezone

    return User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=AuthService.hash_password(password),
        created_at=datetime.now(timezone.utc),
        login_attempts=0,
    )


@pytest.mark.asyncio
async def test_register_success(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = None
    user_repo.save.return_value = None

    result = await auth_service.register("newuser", "new@example.com", "pass1234")

    assert result["access_token"]
    assert result["user"]["username"] == "newuser"
    user_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_username(auth_service, user_repo):
    user_repo.find_by_username.return_value = _make_user()

    with pytest.raises(AuthException) as exc_info:
        await auth_service.register("taken", "new@example.com", "pass1234")
    assert exc_info.value.code == 2010


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = _make_user()

    with pytest.raises(AuthException) as exc_info:
        await auth_service.register("newuser", "taken@example.com", "pass1234")
    assert exc_info.value.code == 2011


@pytest.mark.asyncio
async def test_login_success(auth_service, user_repo):
    user = _make_user()
    user_repo.find_by_email.return_value = user
    user_repo.update.return_value = None

    result = await auth_service.login("test@example.com", "pass1234")

    assert result["access_token"]
    assert result["user"]["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service, user_repo):
    user = _make_user()
    user_repo.find_by_email.return_value = user
    user_repo.update.return_value = None

    with pytest.raises(AuthException) as exc_info:
        await auth_service.login("test@example.com", "wrongpass1")
    assert exc_info.value.code == 1001


@pytest.mark.asyncio
async def test_login_nonexistent_email(auth_service, user_repo):
    user_repo.find_by_email.return_value = None

    with pytest.raises(AuthException) as exc_info:
        await auth_service.login("nope@example.com", "pass1234")
    assert exc_info.value.code == 1001


@pytest.mark.asyncio
async def test_login_locked_account(auth_service, user_repo):
    from datetime import datetime, timedelta, timezone

    user = _make_user()
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    user_repo.find_by_email.return_value = user

    with pytest.raises(AuthException) as exc_info:
        await auth_service.login("test@example.com", "pass1234")
    assert exc_info.value.code == 1002


@pytest.mark.asyncio
async def test_forgot_password_existing_email(auth_service, user_repo, reset_repo):
    user = _make_user()
    user_repo.find_by_email.return_value = user
    reset_repo.save.return_value = None

    token = await auth_service.forgot_password("test@example.com")

    assert token is not None
    reset_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_forgot_password_nonexistent_email(auth_service, user_repo):
    user_repo.find_by_email.return_value = None

    token = await auth_service.forgot_password("nope@example.com")
    assert token is None


@pytest.mark.asyncio
async def test_reset_password_success(auth_service, user_repo, reset_repo):
    import secrets
    import uuid
    from datetime import datetime, timezone

    user = _make_user()
    reset = PasswordReset(
        id=str(uuid.uuid4()),
        user_id=user.id,
        token=secrets.token_urlsafe(32),
        created_at=datetime.now(timezone.utc),
        used=False,
    )

    reset_repo.find_by_token.return_value = reset
    user_repo.find_by_id.return_value = user
    user_repo.update.return_value = None
    reset_repo.update.return_value = None

    await auth_service.reset_password(reset.token, "newpass1234")

    user_repo.update.assert_called_once()
    reset_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(auth_service, reset_repo):
    reset_repo.find_by_token.return_value = None

    with pytest.raises(AuthException) as exc_info:
        await auth_service.reset_password("invalid", "newpass1234")
    assert exc_info.value.code == 1003


@pytest.mark.asyncio
async def test_check_username(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    assert await auth_service.check_username("available") is True

    user_repo.find_by_username.return_value = _make_user()
    assert await auth_service.check_username("taken") is False
