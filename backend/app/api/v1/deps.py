"""FastAPI 依赖：Bearer token 鉴权 → 当前用户。"""

from fastapi import Header, Request

from app.core.envelope import ApiError
from app.core.security import ExpiredTokenError, InvalidTokenError, decode_token
from app.models.user import User


def get_current_user(request: Request, authorization: str | None = Header(default=None)) -> User:
    """解析 Authorization: Bearer <token>，验签 + 过期 + 黑名单，返回当前用户。

    与后端契约一致：未登录 / token 无效 / 过期 → 401。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "未登录或登录已过期，请重新登录")
    token = authorization[7:].strip()
    try:
        claims = decode_token(token)
    except ExpiredTokenError:
        raise ApiError(401, "未登录或登录已过期，请重新登录") from None
    except InvalidTokenError:
        raise ApiError(401, "未登录或登录已过期，请重新登录") from None

    token_repo = request.app.state.token_repository
    if token_repo.is_revoked(claims["jti"]):
        raise ApiError(401, "未登录或登录已过期，请重新登录")

    user_repo = request.app.state.user_repository
    try:
        user_id = int(claims["sub"])
    except (TypeError, ValueError):
        raise ApiError(401, "未登录或登录已过期，请重新登录") from None
    user = user_repo.by_id(user_id)
    if user is None:
        raise ApiError(401, "未登录或登录已过期，请重新登录")
    return user
