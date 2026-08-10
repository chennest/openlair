"""AI 助手：会话表 + 消息表（无硬外键，逻辑关联 users.id）。"""

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssistantSession(Base):
    """assistant_sessions 表：AI 助手会话（每个会话独立上下文）。"""

    __tablename__ = "assistant_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 users.id（无硬外键）
    title: Mapped[str] = mapped_column(String(100), default="新会话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class AssistantMessage(Base):
    """assistant_messages 表：会话内消息（role=user/assistant；meta 存确认计划/工具结果等扩展信息）。"""

    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 assistant_sessions.id
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
