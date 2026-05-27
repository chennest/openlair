from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from lairservice.db.base import Base
from lairservice.db.session import SessionFactory
from lairservice.modules.base import ModuleContext


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class NotesRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create(self, *, user_id: str, content: str) -> Note:
        with self._session_factory() as session:
            note = Note(user_id=user_id, content=content, created_at=datetime.now(UTC))
            session.add(note)
            session.commit()
            session.refresh(note)
            return note

    def list_by_user(self, *, user_id: str) -> list[Note]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(Note).where(Note.user_id == user_id).order_by(Note.created_at.desc(), Note.id.desc())
                )
            )


class NotesService:
    name = "notes"

    def __init__(self, repository: NotesRepository) -> None:
        self._repository = repository

    async def handle(self, *, message: str, context: ModuleContext) -> str:
        content = self._extract_note_content(message)
        note = self._repository.create(user_id=context.user_id, content=content)
        return f"已记录笔记 #{note.id}：{note.content}"

    def list_notes(self, *, user_id: str) -> list[Note]:
        return self._repository.list_by_user(user_id=user_id)

    def _extract_note_content(self, message: str) -> str:
        content = message.strip()
        prefixes = ("记录一下", "记一下", "记录", "笔记", "note", "notes")
        lowered = content.lower()
        for prefix in prefixes:
            if lowered.startswith(prefix):
                content = content[len(prefix) :].strip(" ：:，,。")
                break
        return content or message.strip()
