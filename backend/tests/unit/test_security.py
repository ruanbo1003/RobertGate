"""安全基础设施：bcrypt 哈希与 JWT 令牌（原 AuthService 静态方法的行为锁）。"""

from datetime import datetime, timedelta, timezone

from jose import jwt

from app.config import get_settings
from app.infrastructure.security.jwt import JoseTokens
from app.infrastructure.security.password import BcryptHasher


def test_hash_verify_roundtrip():
    hasher = BcryptHasher()
    hashed = hasher.hash("pass1234")
    assert hashed != "pass1234"
    assert hasher.verify("pass1234", hashed) is True
    assert hasher.verify("wrongpass", hashed) is False


def test_hash_is_salted():
    hasher = BcryptHasher()
    assert hasher.hash("pass1234") != hasher.hash("pass1234")


def test_token_roundtrip():
    tokens = JoseTokens()
    assert tokens.decode(tokens.create("u1")) == "u1"


def test_token_payload_shape():
    """payload 结构是对外契约的一部分：sub + exp，别的字段都不能多。"""
    settings = get_settings()
    payload = jwt.decode(
        JoseTokens().create("u1"),
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert set(payload) == {"sub", "exp"}
    assert payload["sub"] == "u1"


def test_ttl_seconds_matches_settings():
    assert JoseTokens().ttl_seconds == get_settings().JWT_EXPIRE_HOURS * 3600


def test_decode_garbage_returns_none():
    assert JoseTokens().decode("not-a-token") is None


def test_decode_expired_returns_none():
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "u1", "exp": datetime.now(timezone.utc) - timedelta(hours=1)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    assert JoseTokens().decode(expired) is None


def test_decode_wrong_secret_returns_none():
    settings = get_settings()
    foreign = jwt.encode(
        {"sub": "u1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        "some-other-secret",
        algorithm=settings.JWT_ALGORITHM,
    )
    assert JoseTokens().decode(foreign) is None
