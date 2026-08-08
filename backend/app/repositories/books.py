from datetime import UTC, datetime

from sqlalchemy import delete, select

from app.db.session import SessionFactory
from app.models.book import Book, BookMember
from app.models.budget import Budget
from app.models.transaction import Transaction


class BookRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def list_all(self, user_id: int | None = None) -> list[Book]:
        """账本列表：可选按成员过滤（多用户隔离），排除已删除。"""
        with self._session_factory() as session:
            stmt = select(Book).where(Book.deleted_at.is_(None))
            if user_id is not None:
                stmt = (
                    stmt.join(BookMember, BookMember.book_id == Book.id)
                    .where(BookMember.user_id == user_id)
                    .distinct()
                )
            return list(session.scalars(stmt.order_by(Book.id)))

    def list_trash(self, user_id: int | None = None) -> list[Book]:
        """回收站列表：可选按成员过滤，排除已恢复。"""
        with self._session_factory() as session:
            stmt = select(Book).where(Book.deleted_at.is_not(None))
            if user_id is not None:
                stmt = (
                    stmt.join(BookMember, BookMember.book_id == Book.id)
                    .where(BookMember.user_id == user_id)
                    .distinct()
                )
            return list(session.scalars(stmt.order_by(Book.deleted_at.desc())))

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

    # ---------- 回收站（软删除） ----------

    def soft_delete(self, book_id: int) -> None:
        """软删除：置 deleted_at，账本进回收站（流水/预算/成员保留）。"""
        with self._session_factory() as session:
            book = session.get(Book, book_id)
            if book is not None:
                book.deleted_at = datetime.now(UTC)
                session.commit()

    def restore(self, book_id: int) -> None:
        """恢复：清 deleted_at，账本连同原数据回到正常列表。"""
        with self._session_factory() as session:
            book = session.get(Book, book_id)
            if book is not None:
                book.deleted_at = None
                session.commit()

    def purge(self, book_id: int) -> None:
        """彻底删除：级联清流水/预算/成员后物理删除账本。"""
        with self._session_factory() as session:
            session.execute(delete(Transaction).where(Transaction.book_id == book_id))
            session.execute(delete(Budget).where(Budget.book_id == book_id))
            session.execute(delete(BookMember).where(BookMember.book_id == book_id))
            book = session.get(Book, book_id)
            if book is not None:
                session.delete(book)
            session.commit()
