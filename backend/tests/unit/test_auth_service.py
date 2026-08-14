import pytest

from app.application.services.auth_service import AuthService
from app.domain.errors import AuthException
from app.domain.models.user import User
from app.infrastructure.security.jwt import JoseTokens
from app.infrastructure.security.password import BcryptHasher

HASHER = BcryptHasher()


@pytest.fixture
def user_repo(uow):
    return uow.users


@pytest.fixture
def auth_service(uow):
    return AuthService(uow, HASHER, JoseTokens())


def _make_user(username="testuser", email="test@example.com", password="pass1234"):
    import uuid
    from datetime import datetime, timezone

    return User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        hashed_password=HASHER.hash(password),
        role="user",
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_register_success(auth_service, uow, user_repo):
    user_repo.find_by_username.return_value = None
    user_repo.find_by_email.return_value = None

    result = await auth_service.register("newuser", "new@example.com", "pass1234")

    assert result.access_token
    assert result.user.username == "newuser"
    user_repo.add.assert_called_once()
    # 写用例事务边界：恰好提交一次
    assert uow.commit.await_count == 1


@pytest.mark.asyncio
async def test_register_duplicate_does_not_commit(auth_service, uow, user_repo):
    user_repo.find_by_username.return_value = _make_user()

    with pytest.raises(AuthException):
        await auth_service.register("taken", "new@example.com", "pass1234")
    uow.commit.assert_not_awaited()


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

    result = await auth_service.login("test@example.com", "pass1234")

    assert result.access_token
    assert result.user.username == "testuser"


@pytest.mark.asyncio
async def test_login_wrong_password(auth_service, user_repo):
    user = _make_user()
    user_repo.find_by_email.return_value = user

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
async def test_check_username(auth_service, user_repo):
    user_repo.find_by_username.return_value = None
    assert await auth_service.check_username("available") is True

    user_repo.find_by_username.return_value = _make_user()
    assert await auth_service.check_username("taken") is False


@pytest.mark.asyncio
async def test_get_me_success(auth_service, user_repo):
    user = _make_user()
    user_repo.find_by_id.return_value = user

    result = await auth_service.get_me(user.id)

    assert result.id == user.id
    assert result.username == user.username
    assert result.email == user.email
    assert result.role == "user"
    assert result.created_at == user.created_at


@pytest.mark.asyncio
async def test_get_me_not_found(auth_service, user_repo):
    user_repo.find_by_id.return_value = None

    with pytest.raises(AuthException) as exc_info:
        await auth_service.get_me("nonexistent-id")
    assert exc_info.value.code == 1001
