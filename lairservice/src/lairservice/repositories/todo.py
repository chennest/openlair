from sqlalchemy import select

from lairservice.db.session import SessionFactory
from lairservice.models.todo import TodoItem


class TodoRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_by_user(self, user_id: int) -> list[TodoItem]:
        with self._session_factory() as session:
            return list(session.scalars(select(TodoItem).where(TodoItem.user_id == user_id).order_by(TodoItem.id)))

    def get(self, todo_id: int) -> TodoItem | None:
        with self._session_factory() as session:
            return session.get(TodoItem, todo_id)

    def create(self, *, user_id: int, text: str, quadrant: str, due: str) -> TodoItem:
        with self._session_factory() as session:
            item = TodoItem(user_id=user_id, text=text, quadrant=quadrant, done=False, due=due)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update(self, todo_id: int, patch: dict) -> TodoItem | None:
        with self._session_factory() as session:
            item = session.get(TodoItem, todo_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    def delete(self, todo_id: int) -> bool:
        with self._session_factory() as session:
            item = session.get(TodoItem, todo_id)
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True
