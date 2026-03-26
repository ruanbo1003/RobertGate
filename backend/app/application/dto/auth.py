from dataclasses import dataclass


@dataclass
class RegisterDTO:
    username: str
    email: str
    password: str


@dataclass
class LoginDTO:
    email: str
    password: str


@dataclass
class ResetPasswordDTO:
    token: str
    password: str


@dataclass
class AuthResultDTO:
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user_id: str = ""
    username: str = ""
    email: str = ""
    created_at: str = ""
