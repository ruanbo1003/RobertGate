from unittest.mock import AsyncMock

import pytest

from app.application.dto.auth import LoginDTO, RegisterDTO, ResetPasswordDTO
from app.application.services.auth_service import AuthError, AuthService
from app.application.services.password_hasher import hash_password
from app.domain.models.password_reset import PasswordReset
from app.domain.models.user import User


@pytest.fixture
def user_repo():
    return AsyncMock()


@pytest.fixture
def reset_repo():
    return AsyncMock()


@pytest.fixture
def auth_service(user_repo, reset_repo):
    return AuthService(user_repo=user_repo, reset_repo=reset_repo)


@pytest.mark.asyncio
async def test_register_success(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = None
    user_repo.save.return_value = None

    result = await auth_service.register(
        RegisterDTO(username="newuser", email="new@example.com", password="pass1234")
    )

    assert result.access_token
    assert result.username == "newuser"
    assert result.email == "new@example.com"
    user_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_register_duplicate_username(auth_service, user_repo):
    user_repo.find_by_username.return_value = User.create("taken", "x@x.com", "h")

    with pytest.raises(AuthError) as exc_info:
        await auth_service.register(
            RegisterDTO(username="taken", email="new@example.com", password="pass1234")
        )
    assert exc_info.value.code == 2010


@pytest.mark.asyncio
async def test_register_duplicate_email(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = User.create("other", "taken@example.com", "h")

    with pytest.raises(AuthError) as exc_info:
        await auth_service.register(
            RegisterDTO(username="newuser", email="taken@example.com", password="pass1234")
        )
    assert exc_info.value.code == 2011


@pytest.mark.asyncio
async def test_login_success(auth_service, user_repo):
    hashed = hash_password("pass1234")
    user = User.create("testuser", "test@example.com", hashed)
    user_repo.find_by_email.return_value = user
    user_repo.update.return_value = None

    result = await auth_service.login(
        LoginDTO(email="test@example.com", password="pass1234")
    )

    assert result.access_token
    assert result.username == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service, user_repo):
    hashed = hash_password("pass1234")
    user = User.create("testuser", "test@example.com", hashed)
    user_repo.find_by_email.return_value = user
    user_repo.update.return_value = None

    with pytest.raises(AuthError) as exc_info:
        await auth_service.login(
            LoginDTO(email="test@example.com", password="wrongpass1")
        )
    assert exc_info.value.code == 1001


@pytest.mark.asyncio
async def test_login_nonexistent_email(auth_service, user_repo):
    user_repo.find_by_email.return_value = None

    with pytest.raises(AuthError) as exc_info:
        await auth_service.login(
            LoginDTO(email="nope@example.com", password="pass1234")
        )
    assert exc_info.value.code == 1001


@pytest.mark.asyncio
async def test_login_locked_account(auth_service, user_repo):
    from datetime import datetime, timedelta, timezone

    hashed = hash_password("pass1234")
    user = User.create("testuser", "test@example.com", hashed)
    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=10)
    user_repo.find_by_email.return_value = user

    with pytest.raises(AuthError) as exc_info:
        await auth_service.login(
            LoginDTO(email="test@example.com", password="pass1234")
        )
    assert exc_info.value.code == 1002


@pytest.mark.asyncio
async def test_forgot_password_existing_email(auth_service, user_repo, reset_repo):
    user = User.create("testuser", "test@example.com", "h")
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
    user = User.create("testuser", "test@example.com", hash_password("oldpass1"))
    reset = PasswordReset.create(user.id)

    reset_repo.find_by_token.return_value = reset
    user_repo.find_by_id.return_value = user
    user_repo.update.return_value = None
    reset_repo.update.return_value = None

    await auth_service.reset_password(
        ResetPasswordDTO(token=reset.token, password="newpass1234")
    )

    user_repo.update.assert_called_once()
    reset_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(auth_service, reset_repo):
    reset_repo.find_by_token.return_value = None

    with pytest.raises(AuthError) as exc_info:
        await auth_service.reset_password(
            ResetPasswordDTO(token="invalid", password="newpass1234")
        )
    assert exc_info.value.code == 1003


@pytest.mark.asyncio
async def test_check_username(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    assert await auth_service.check_username("available") is True

    user_repo.find_by_username.return_value = User.create("taken", "x@x.com", "h")
    assert await auth_service.check_username("taken") is False
