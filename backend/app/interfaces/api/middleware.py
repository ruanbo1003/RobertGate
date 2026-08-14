import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.domain.errors import AppException, codes
from app.interfaces.api.response import ApiResponse

access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.error")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            return await call_next(request)
        except AppException as e:
            return ApiResponse(code=e.code, message=e.message)
        except ValueError as e:
            return ApiResponse(code=codes.PARAM_INVALID, message=str(e))
        except Exception as e:
            error_logger.exception(f"Unhandled error: {e}")
            return ApiResponse(code=codes.INTERNAL_ERROR, message="服务器内部错误")


class ApiLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)

        path = request.url.path
        if path not in ("/api/health", "/docs", "/openapi.json"):
            access_logger.info(
                "%s %s status=%s duration=%sms",
                request.method,
                path,
                response.status_code,
                duration,
            )

        return response
