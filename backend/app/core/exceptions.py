class AppException(Exception):
    """Base application exception."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class AuthException(AppException):
    """Authentication/authorization errors (1000-1999)."""
    pass


class ParamException(AppException):
    """Parameter validation errors (2000-2999)."""
    pass


class ServerException(AppException):
    """Server internal errors (5000-5999)."""
    pass
