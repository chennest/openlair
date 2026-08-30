"""系统设置仓储：key-value 读写（allow_register 等）。"""

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.setting import Setting


class SettingRepository:
    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def get(self, key: str, default: str = "") -> str:
        """读取设置值；不存在返回 default。"""
        with self._session_factory() as session:
            row = session.scalar(select(Setting).where(Setting.key == key))
            return row.value if row else default

    def set(self, key: str, value: str) -> None:
        """写入/更新设置值（手动改库通常直接 SQL，此方法供程序内部使用）。"""
        with self._session_factory() as session:
            row = session.scalar(select(Setting).where(Setting.key == key))
            if row:
                row.value = value
            else:
                session.add(Setting(key=key, value=value))
            session.commit()
