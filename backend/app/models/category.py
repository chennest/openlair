from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Category(Base):
    """categories 表：收支分类。

    - 系统预置：user_id IS NULL（seed 写入，id 固定 1-26，供外键引用，不可增删改）
    - 用户自定义：user_id = 创建者 id（仅创建者可改名/删除，所有账本成员可见共用）
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(8), index=True)  # 支出 | 收入
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)  # AI 兜底分类（「其他」）
    user_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None)  # NULL=系统预置
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
