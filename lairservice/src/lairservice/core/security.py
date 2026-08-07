"""安全层：JWT（HS256）签发/验签 + 密码哈希。

- JWT 使用 PyJWT（RFC 7519 标准实现）：`jwt.encode` / `jwt.decode(token, secret, algorithms=["HS256"])`。
- 密码哈希使用 hashlib.scrypt（NIST 推荐 KDF），格式 `scrypt$salt$hash`；
  生产环境可替换为 passlib/bcrypt。
- 登出黑名单：jti 写入 revoked_tokens 表（等价于 Redis 黑名单方案）。
- JWT 密钥读取优先级（config.resolve_env_value）：进程环境 OPENLAIR_JWT_SECRET →
  项目根 .env（lairservice/.env）→ 开发默认。
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from lairservice.config import resolve_env_value

# 开发默认密钥（>= 32 字节）；生产必须通过 OPENLAIR_JWT_SECRET 配置，见 .env.example
DEV_SECRET = "openlair-dev-secret-key-0123456789ab"
ACCESS_TOKEN_TTL = timedelta(days=7)  # 与 mock 一致：7 天


def resolve_jwt_secret() -> str:
    """JWT 密钥解析：进程环境 → 项目根 .env → 开发默认。"""
    return resolve_env_value("OPENLAIR_JWT_SECRET", DEV_SECRET) or DEV_SECRET


SECRET_KEY = resolve_jwt_secret()


# ---------- JWT ----------

def sign_token(user_id: int) -> tuple[str, str]:
    """签发 JWT（HS256），返回 (token, jti)。"""
    now = datetime.now(UTC)
    jti = secrets.token_hex(8)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + ACCESS_TOKEN_TTL,
        "jti": jti,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token, jti


class InvalidTokenError(Exception):
    pass


class ExpiredTokenError(Exception):
    pass


def decode_token(token: str) -> dict:
    """验签 + 过期检查，返回 claims；无效签名抛 InvalidTokenError，过期抛 ExpiredTokenError。"""
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("token 已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("token 无效") from exc
    if not claims.get("sub") or not claims.get("jti"):
        raise InvalidTokenError("token 缺少必要声明")
    return claims


# ---------- 密码哈希（scrypt，模拟 bcrypt 语义） ----------

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_KEYLEN = 64


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt.encode(), n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_KEYLEN
    )
    return f"scrypt${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, expected_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=SCRYPT_KEYLEN
        )
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (ValueError, TypeError):
        return False
