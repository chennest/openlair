from sqlalchemy import select

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
            session.add(RevokedToken(jti=jti, user_id=user_id))
            session.commit()
