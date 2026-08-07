"""认证服务：注册 / 登录 / 登出 / 当前用户。"""

import re

from lairservice.core.envelope import ApiError
from lairservice.core.security import (
    ExpiredTokenError,
    InvalidTokenError,
    decode_token,
    hash_password,
    sign_token,
    verify_password,
)
from lairservice.models.user import User
from lairservice.repositories.tokens import TokenRepository
from lairservice.repositories.users import UserRepository
from lairservice.services import iso_z

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
AVATAR_COLORS = ["#0071e3", "#30d158", "#ff6b00", "#5e5ce6", "#ff375f", "#1d9bf0", "#ff9f0a"]


def user_dto(user: User) -> dict:
    """用户 DTO：绝不返回 password_hash（与后端契约一致）。"""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email or "",
        "avatarColor": user.avatar_color,
        "createdAt": iso_z(user.created_at),
    }


class AuthService:
    def __init__(self, users: UserRepository, tokens: TokenRepository) -> None:
        self._users = users
        self._tokens = tokens

    def register(self, *, name: str, email: str, password: str) -> dict:
        name = name.strip()
        email = email.strip().lower()
        if not name or len(name) > 20:
            raise ApiError(400, "昵称需为 1-20 个字符")
        if not EMAIL_RE.match(email):
            raise ApiError(400, "邮箱格式不正确")
        if not (6 <= len(password) <= 64):
            raise ApiError(400, "密码需为 6-64 位")
        if self._users.exists_email(email):
            raise ApiError(409, "该邮箱已被注册")
        user = self._users.create(
            name=name,
            email=email,
            password_hash=hash_password(password),
            avatar_color=AVATAR_COLORS[hash(email) % len(AVATAR_COLORS)],
        )
        token, _ = sign_token(user.id)
        return {"token": token, "user": user_dto(user)}

    def login(self, *, email: str, password: str) -> dict:
        email = (email or "").strip().lower()
        if not email:
            raise ApiError(400, "请输入邮箱")
        if not password:
            raise ApiError(400, "请输入密码")
        user = self._users.by_email(email)
        # 不区分「用户不存在」与「密码错误」，避免账号探测
        if user is None or user.password_hash is None or not verify_password(password, user.password_hash):
            raise ApiError(401, "邮箱或密码错误")
        token, _ = sign_token(user.id)
        return {"token": token, "user": user_dto(user)}

    def logout(self, *, token: str, user_id: int) -> None:
        try:
            claims = decode_token(token)
        except (InvalidTokenError, ExpiredTokenError):
            return  # token 已失效则无需黑名单
        self._tokens.revoke(jti=claims["jti"], user_id=user_id)

    def me(self, *, user_id: int) -> dict:
        user = self._users.by_id(user_id)
        if user is None:
            raise ApiError(401, "用户不存在")
        return user_dto(user)
