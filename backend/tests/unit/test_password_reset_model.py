import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.models.password_reset import PasswordReset
from app.service.auth_service import AuthService


def _make_reset():
    return PasswordReset(
        id=str(uuid.uuid4()),
        user_id="user-123",
        token=secrets.token_urlsafe(32),
        created_at=datetime.now(timezone.utc),
        used=False,
    )


def test_is_valid_when_fresh():
    reset = _make_reset()
    assert AuthService.is_reset_valid(reset)


def test_is_invalid_when_used():
    reset = _make_reset()
    reset.used = True
    assert not AuthService.is_reset_valid(reset)


def test_is_invalid_when_expired():
    reset = _make_reset()
    reset.created_at = datetime.now(timezone.utc) - timedelta(minutes=31)
    assert not AuthService.is_reset_valid(reset)
