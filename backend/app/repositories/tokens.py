from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.core.security import ACCESS_TOKEN_TTL
from app.db.session import SessionFactory
from app.models.revoked_token import RevokedToken


class TokenRepository:
    """JWT 黑名单（登出后的 jti 记录）。"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def is_revoked(self, jti: str) -> bool:
        with self._session_factory() as session:
            return session.scalar(select(RevokedToken.id).where(RevokedToken.jti == jti)) is not None

    def revoke(self, *, jti: str, user_id: int) -> None:
        with self._session_factory() as session:
            # 惰性清理：token 过期（TTL 窗口）后的黑名单记录不会再被校验到，顺手删掉，
            # 保证表只保留 TTL 窗口内的数据，无需定时任务。
            cutoff = datetime.now(UTC) - ACCESS_TOKEN_TTL
            session.execute(delete(RevokedToken).where(RevokedToken.revoked_at < cutoff))
            session.add(RevokedToken(jti=jti, user_id=user_id))
            session.commit()
