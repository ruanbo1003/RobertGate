from datetime import datetime, timedelta, timezone

from app.domain.models.user import User


def test_create_user():
    user = User.create(username="testuser", email="test@example.com", hashed_password="hashed")
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.login_attempts == 0
    assert user.locked_until is None


def test_user_not_locked_by_default():
    user = User.create(username="test", email="t@t.com", hashed_password="h")
    assert not user.is_locked


def test_record_failed_login_locks_after_max_attempts():
    user = User.create(username="test", email="t@t.com", hashed_password="h")
    for _ in range(5):
        user.record_failed_login(max_attempts=5, lock_minutes=15)
    assert user.is_locked
    assert user.login_attempts == 5


def test_reset_login_attempts():
    user = User.create(username="test", email="t@t.com", hashed_password="h")
    for _ in range(3):
        user.record_failed_login()
    user.reset_login_attempts()
    assert user.login_attempts == 0
    assert user.locked_until is None


def test_lock_expires():
    user = User.create(username="test", email="t@t.com", hashed_password="h")
    user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert not user.is_locked
