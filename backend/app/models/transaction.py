from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    """transactions 表：交易流水（categoryId → categories.id，bookId → books.id，userId → users.id）。"""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(8), index=True)  # 支出 | 收入
    category_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 categories.id（无硬外键）
    book_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 books.id（无硬外键）
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    date: Mapped[date] = mapped_column(Date, index=True)  # YYYY-MM-DD
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
