from collections.abc import Callable
from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


SessionFactory = Callable[[], Session]

# backend/ 根目录（alembic.ini 与 migrations/ 所在）
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def create_database_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        _ensure_sqlite_parent_exists(database_url)
        return create_engine(database_url, connect_args={"check_same_thread": False})
    # pool_pre_ping：MySQL/PostgreSQL 空闲断连（wait_timeout/网络波动）时自动重连，
    # 避免首次查询报 Lost connection
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    """引导数据库 schema（create_all 与 Alembic 双轨协调）。

    - 已有库（存在 alembic_version 表）：跳过 create_all，schema 演进完全交给
      Alembic 迁移（prestart 的 `alembic upgrade head`），避免迁移重放建表 DDL
      与 create_all 已建的表冲突（MySQL 1050 崩溃）。
    - 全新库（无 alembic_version 表）：create_all 建全量表后 `stamp head`，
      让 alembic_version 与表结构对齐，后续 `upgrade head` 成为 no-op。
    """
    inspector = sa.inspect(engine)
    if "alembic_version" in inspector.get_table_names():
        return
    Base.metadata.create_all(engine)
    _stamp_head(engine)


def _stamp_head(engine: Engine) -> None:
    """把全新库的 alembic_version 标记为 head（表结构已由 create_all 建好）。

    不通过 alembic command.stamp：migrations/env.py 会用 get_settings().database_url
    无条件覆盖 URL，导致写错库。这里用 ScriptDirectory 读取 head revision，
    再直接向同一 engine 写 alembic_version 表。
    """
    cfg = AlembicConfig(str(_PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_PROJECT_ROOT / "migrations"))
    head = ScriptDirectory.from_config(cfg).get_current_head()
    if not head:
        return  # 无迁移脚本：无需版本记录

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
            )
        )
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES (:v)"), {"v": head})


def _ensure_sqlite_parent_exists(database_url: str) -> None:
    prefix = "sqlite+pysqlite:///"
    if not database_url.startswith(prefix):
        return

    raw_path = database_url.removeprefix(prefix)
    if raw_path == ":memory:":
        return

    db_path = Path(raw_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
