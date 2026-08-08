from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Book(Base):
    """books 表：账本（个人 / 共享；「家庭」只是共享账本的一种场景）。"""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    type: Mapped[str] = mapped_column(String(16))  # personal | shared
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    # 软删除：NULL = 正常；非 NULL = 在回收站（删除时间）
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None, index=True)


class BookMember(Base):
    """book_members 表：账本成员关系（owner 不可移除）。"""

    __tablename__ = "book_members"
    __table_args__ = (UniqueConstraint("book_id", "user_id", name="uq_book_member"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 books.id（无硬外键）
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    role: Mapped[str] = mapped_column(String(16), default="editor")  # owner | editor
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
