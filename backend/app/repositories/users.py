from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.user import User


class UserRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def by_id(self, user_id: int) -> User | None:
        with self._session_factory() as session:
            return session.get(User, user_id)

    def by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            return session.scalar(select(User).where(User.email == email))

    def exists_email(self, email: str) -> bool:
        with self._session_factory() as session:
            return session.scalar(select(User.id).where(User.email == email)) is not None

    def create(
        self,
        *,
        name: str,
        email: str | None = None,
        password_hash: str | None = None,
        avatar_color: str,
    ) -> User:
        with self._session_factory() as session:
            user = User(name=name, email=email, password_hash=password_hash, avatar_color=avatar_color)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
