from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Budget(Base):
    """budgets 表：月度预算（按账本隔离，month = 'YYYY-MM'）。"""

    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("book_id", "month", name="uq_budget_book_month"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 books.id（无硬外键）
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    expense_limit: Mapped[float] = mapped_column(Numeric(12, 2), default=5000)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
