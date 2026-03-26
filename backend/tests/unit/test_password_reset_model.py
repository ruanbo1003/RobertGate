from datetime import datetime, timedelta, timezone

from app.domain.models.password_reset import PasswordReset


def test_create_password_reset():
    reset = PasswordReset.create(user_id="user-123")
    assert reset.user_id == "user-123"
    assert len(reset.token) > 0
    assert not reset.used


def test_is_valid_when_fresh():
    reset = PasswordReset.create(user_id="user-123")
    assert reset.is_valid


def test_is_invalid_when_used():
    reset = PasswordReset.create(user_id="user-123")
    reset.mark_used()
    assert not reset.is_valid


def test_is_invalid_when_expired():
    reset = PasswordReset.create(user_id="user-123")
    reset.created_at = datetime.now(timezone.utc) - timedelta(minutes=31)
    assert reset.is_expired
    assert not reset.is_valid
