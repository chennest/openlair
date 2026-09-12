from datetime import date

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.day import Day


class DayRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_by_user(self, user_id: int) -> list[Day]:
        with self._session_factory() as session:
            stmt = select(Day).where(Day.user_id == user_id).order_by(Day.pinned.desc(), Day.id)
            return list(session.scalars(stmt))

    def get(self, day_id: int) -> Day | None:
        with self._session_factory() as session:
            return session.get(Day, day_id)

    def create(self, *, user_id: int, title: str, date: date, emoji: str, repeat: str, pinned: bool) -> Day:
        with self._session_factory() as session:
            item = Day(user_id=user_id, title=title, date=date, emoji=emoji, repeat=repeat, pinned=pinned)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update(self, day_id: int, patch: dict) -> Day | None:
        with self._session_factory() as session:
            item = session.get(Day, day_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    def delete(self, day_id: int) -> bool:
        with self._session_factory() as session:
            item = session.get(Day, day_id)
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True
