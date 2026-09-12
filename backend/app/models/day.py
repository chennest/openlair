from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Day(Base):
    """days 表：倒数日 / 纪念日（repeat = once 一次性 / yearly 每年 / monthly 每月）。"""

    __tablename__ = "days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    title: Mapped[str] = mapped_column(String(60))
    emoji: Mapped[str] = mapped_column(String(8), default="")
    date: Mapped[date] = mapped_column(Date)  # 目标日期（重复时只取月/日展开下一次）
    repeat: Mapped[str] = mapped_column(String(10), default="once")
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
