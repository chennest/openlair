from sqlalchemy import select

from lairservice.db.session import SessionFactory
from lairservice.models.habit import Habit


class HabitRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_by_user(self, user_id: int) -> list[Habit]:
        with self._session_factory() as session:
            return list(session.scalars(select(Habit).where(Habit.user_id == user_id).order_by(Habit.id)))

    def get(self, habit_id: int) -> Habit | None:
        with self._session_factory() as session:
            return session.get(Habit, habit_id)

    def create(self, *, user_id: int, name: str) -> Habit:
        with self._session_factory() as session:
            item = Habit(user_id=user_id, name=name, streak=0, done=False, week=[False] * 7)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update(self, habit_id: int, patch: dict) -> Habit | None:
        with self._session_factory() as session:
            item = session.get(Habit, habit_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    def delete(self, habit_id: int) -> bool:
        with self._session_factory() as session:
            item = session.get(Habit, habit_id)
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True
