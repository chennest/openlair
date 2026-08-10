"""AI 助手：会话表 + 消息表 + 计划执行日志表（无硬外键，逻辑关联 users.id）。"""

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
    """assistant_messages 表：会话内消息（role=user/assistant；type=消息形态 text|confirm_request|tool_result；meta 存确认计划/工具结果等扩展信息）。"""

    __tablename__ = "assistant_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True)  # 逻辑关联 assistant_sessions.id
    role: Mapped[str] = mapped_column(String(20))
    type: Mapped[str] = mapped_column(String(20), default="text")  # 消息形态：text | confirm_request | tool_result（与 role 正交）
    content: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AssistantPlan(Base):
    """assistant_plans 表：计划执行日志（给系统审计/查询/回传 AI 用，与消息表互补）。

    状态机：pending → executed | cancelled | failed
    """

    __tablename__ = "assistant_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    session_id: Mapped[int] = mapped_column(Integer, index=True)
    tool: Mapped[str] = mapped_column(String(32))
    args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | executed | cancelled | failed
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
