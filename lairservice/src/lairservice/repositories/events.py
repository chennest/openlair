from datetime import date

from sqlalchemy import select

from lairservice.db.session import SessionFactory
from lairservice.models.event import CalendarEvent


class EventRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_by_user(self, user_id: int) -> list[CalendarEvent]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(CalendarEvent).where(CalendarEvent.user_id == user_id).order_by(CalendarEvent.date, CalendarEvent.id)
                )
            )

    def get(self, event_id: int) -> CalendarEvent | None:
        with self._session_factory() as session:
            return session.get(CalendarEvent, event_id)

    def create(
        self, *, user_id: int, title: str, date: date, time: str, location: str
    ) -> CalendarEvent:
        with self._session_factory() as session:
            item = CalendarEvent(user_id=user_id, title=title, date=date, time=time, location=location, done=False)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item

    def update(self, event_id: int, patch: dict) -> CalendarEvent | None:
        with self._session_factory() as session:
            item = session.get(CalendarEvent, event_id)
            if item is None:
                return None
            for key, value in patch.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            session.commit()
            session.refresh(item)
            return item

    def delete(self, event_id: int) -> bool:
        with self._session_factory() as session:
            item = session.get(CalendarEvent, event_id)
            if item is None:
                return False
            session.delete(item)
            session.commit()
            return True
