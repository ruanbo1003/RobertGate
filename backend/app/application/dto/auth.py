from __future__ import annotations

from app.application.dto.base import DTO, IsoDt


class UserOut(DTO):
    id: str
    username: str
    email: str
    role: str
    created_at: IsoDt


class AuthResult(DTO):
    access_token: str
    token_type: str
    expires_in: int
    user: UserOut
