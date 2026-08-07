"""统一 API 响应信封：{ code, message, data }。

与前端契约（mock 层）完全一致：
- 成功：code=200，message="成功"，data 为业务数据
- 失败：code=HTTP 状态码，message 为人类可读错误，data=null
- HTTP 状态码与 code 一致
"""

from typing import Any, Generic, TypeVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

T = TypeVar("T")


class ApiError(Exception):
    """业务错误：status 即 HTTP 状态码与响应 code。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def ok_response(data: Any, message: str = "成功") -> dict[str, Any]:
    return {"code": 200, "message": message, "data": data}


def error_response(status: int, message: str) -> dict[str, Any]:
    return {"code": status, "message": message, "data": None}


def _api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    headers = {}
    if exc.status == 401:
        headers["WWW-Authenticate"] = "Bearer"
    return JSONResponse(status_code=exc.status, content=error_response(exc.status, exc.message), headers=headers)


def _http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    status = exc.status_code
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return JSONResponse(status_code=status, content=error_response(status, detail))


def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content=error_response(500, "服务器内部错误"))


def register_envelope_handlers(app: FastAPI) -> None:
    """注册统一信封异常处理器：ApiError / HTTPException / 兜底 500。"""
    from fastapi import HTTPException

    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(HTTPException, _http_error_handler)
    app.add_exception_handler(Exception, _unhandled_error_handler)
