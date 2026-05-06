import uuid
from datetime import datetime, timedelta, timezone

from app.models.user import User
from app.service.auth_service import AuthService


def _make_user():
    return User(
        id=str(uuid.uuid4()),
        username="test",
        email="t@t.com",
        hashed_password="h",
        created_at=datetime.now(timezone.utc),
        login_attempts=0,
    )


def test_user_not_locked_by_default():
    user = _make_user()
    assert not AuthService.is_user_locked(user)


def test_record_failed_login_locks_after_max_attempts():
    user = _make_user()
    for _ in range(5):
        AuthService.record_failed_login(user, max_attempts=5, lock_minutes=15)
    assert AuthService.is_user_locked(user)
    assert user.login_attempts == 5


def test_reset_login_attempts():
    user = _make_user()
    for _ in range(3):
        AuthService.record_failed_login(user)
    AuthService.reset_login_attempts(user)
    assert user.login_attempts == 0
    assert user.locked_until is None


def test_lock_expires():
    user = _make_user()
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert not AuthService.is_user_locked(user)
