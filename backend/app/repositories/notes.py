from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.note import Note


class NoteRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_by_user(self, user_id: int) -> list[Note]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Note).where(Note.user_id == user_id).order_by(Note.updated_at.desc(), Note.id.desc())
                )
            )

    def get(self, note_id: int) -> Note | None:
        with self._session_factory() as session:
            return session.get(Note, note_id)

    def create(self, *, user_id: int, title: str, summary: str, tags: list[str]) -> Note:
        with self._session_factory() as session:
            note = Note(user_id=user_id, title=title, summary=summary, tags=tags)
            session.add(note)
            session.commit()
            session.refresh(note)
            return note

    def update(self, note_id: int, patch: dict) -> Note | None:
        with self._session_factory() as session:
            note = session.get(Note, note_id)
            if note is None:
                return None
            for key, value in patch.items():
                if hasattr(note, key):
                    setattr(note, key, value)
            session.commit()
            session.refresh(note)
            return note

    def delete(self, note_id: int) -> bool:
        with self._session_factory() as session:
            note = session.get(Note, note_id)
            if note is None:
                return False
            session.delete(note)
            session.commit()
            return True

    # ---------- agent 快速记录 ----------

    def create_quick(self, *, user_id: int, content: str, title: str) -> Note:
        with self._session_factory() as session:
            note = Note(user_id=user_id, content=content, title=title, summary="", tags=[])
            session.add(note)
            session.commit()
            session.refresh(note)
            return note

    def list_content_by_user(self, user_id: int) -> list[Note]:
        """agent 侧：按更新时间倒序取全部（含 content）。"""
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc(), Note.id.desc())
                )
            )
