from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Setting(Base):
    """settings 表：系统设置（key-value 单表）。

    - key 唯一，value 存 JSON 字符串（如 "0"/"1"），新增设置零迁移成本
    - 约定键：
      - allow_register: "0"=禁止注册（默认） / "1"=允许注册
    - 生产修改方式：手动改库（不做管理接口）
    - 注意：列名用 setting_key（key 是 MySQL 保留字，裸 SQL/DDL 会报 1064）
    """

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column("setting_key", String(64), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
