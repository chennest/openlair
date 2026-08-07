from sqlalchemy import select

from lairservice.db.session import SessionFactory
from lairservice.models.book import Book, BookMember


class BookRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_all(self) -> list[Book]:
        with self._session_factory() as session:
            return list(session.scalars(select(Book).order_by(Book.id)))

    def get(self, book_id: int) -> Book | None:
        with self._session_factory() as session:
            return session.get(Book, book_id)

    def create(self, *, name: str, type: str) -> Book:
        with self._session_factory() as session:
            book = Book(name=name, type=type)
            session.add(book)
            session.commit()
            session.refresh(book)
            return book

    def members_of(self, book_id: int) -> list[BookMember]:
        with self._session_factory() as session:
            return list(
                session.scalars(select(BookMember).where(BookMember.book_id == book_id).order_by(BookMember.id))
            )

    def member(self, book_id: int, user_id: int) -> BookMember | None:
        with self._session_factory() as session:
            return session.scalar(
                select(BookMember).where(BookMember.book_id == book_id, BookMember.user_id == user_id)
            )

    def add_member(self, *, book_id: int, user_id: int, role: str) -> BookMember:
        with self._session_factory() as session:
            member = BookMember(book_id=book_id, user_id=user_id, role=role)
            session.add(member)
            session.commit()
            session.refresh(member)
            return member

    def remove_member(self, *, book_id: int, user_id: int) -> None:
        with self._session_factory() as session:
            member = session.scalar(
                select(BookMember).where(BookMember.book_id == book_id, BookMember.user_id == user_id)
            )
            if member is not None:
                session.delete(member)
                session.commit()
