"""API Key 数据访问：哈希查询、列表、创建、撤销、触摸最后使用时间。"""

from datetime import UTC, datetime

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def by_hash(self, key_hash: str) -> ApiKey | None:
        """按哈希查未撤销的 Key（认证用；不更新 last_used_at，由 touch 单独做）。"""
        with self._session_factory() as session:
            return session.scalar(
                select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.revoked_at.is_(None))
            )

    def list_active(self, user_id: int) -> list[ApiKey]:
        """列出用户全部未撤销的 Key（按创建时间倒序）。"""
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(ApiKey)
                    .where(ApiKey.user_id == user_id, ApiKey.revoked_at.is_(None))
                    .order_by(ApiKey.created_at.desc(), ApiKey.id.desc())
                )
            )

    def get(self, key_id: int) -> ApiKey | None:
        with self._session_factory() as session:
            return session.get(ApiKey, key_id)

    def create(self, *, user_id: int, name: str, key_hash: str, prefix: str) -> ApiKey:
        with self._session_factory() as session:
            key = ApiKey(user_id=user_id, name=name, key_hash=key_hash, prefix=prefix)
            session.add(key)
            session.commit()
            session.refresh(key)
            return key

    def revoke(self, key_id: int) -> bool:
        """撤销 Key（置 revoked_at）；已撤销或不存在返回 False。"""
        with self._session_factory() as session:
            key = session.get(ApiKey, key_id)
            if key is None or key.revoked_at is not None:
                return False
            key.revoked_at = datetime.now(UTC)
            session.commit()
            return True

    def touch(self, key_id: int) -> None:
        """记录最后使用时间（认证成功时调用）。"""
        with self._session_factory() as session:
            key = session.get(ApiKey, key_id)
            if key is not None:
                key.last_used_at = datetime.now(UTC)
                session.commit()
