import re

from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not 2 <= len(v) <= 20:
            raise ValueError("用户名需要 2-20 个字符")
        if not re.match(r"^[\w\u4e00-\u9fff]+$", v):
            raise ValueError("用户名只能包含中英文、数字、下划线")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not 8 <= len(v) <= 32:
            raise ValueError("密码需要 8-32 个字符")
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码需要包含字母和数字")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not 8 <= len(v) <= 32:
            raise ValueError("密码需要 8-32 个字符")
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("密码需要包含字母和数字")
        return v


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    created_at: str


class AuthDataResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse


class AvailabilityResponse(BaseModel):
    available: bool
