"""FastAPI 依赖：Bearer token / API Key 鉴权 → 当前用户。

两种等价凭证（以 X-API-Key 优先，不存在时回退 JWT）：
- `Authorization: Bearer <JWT>`：登录态（7 天 TTL，登出/过期失效）。
- `X-API-Key: <ol_xxx>`：用户级 API Key（长效，可独立撤销），供 MCP/第三方客户端访问所有接口。
"""

from fastapi import Header, Request

from app.core.envelope import ApiError
from app.core.security import ExpiredTokenError, InvalidTokenError, decode_token, hash_api_key
from app.models.user import User


def _resolve_api_key(request: Request, api_key: str) -> User | None:
    """API Key 认证：哈希比对 → 未撤销 → 生效用户；成功时更新 last_used_at。"""
    api_key_repo = request.app.state.api_key_repository
    key = api_key_repo.by_hash(hash_api_key(api_key))
    if key is None:
        return None
    user = request.app.state.user_repository.by_id(key.user_id)
    if user is None:
        return None
    api_key_repo.touch(key.id)
    return user


def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> User:
    """解析凭证并返回当前用户；无效/过期/已撤销 → 401（与后端契约一致）。"""
    if x_api_key:
        user = _resolve_api_key(request, x_api_key.strip())
        if user is not None:
            return user
        raise ApiError(401, "未登录或登录已过期，请重新登录")

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
