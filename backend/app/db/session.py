from collections.abc import Callable
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base


SessionFactory = Callable[[], Session]


def create_database_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        _ensure_sqlite_parent_exists(database_url)
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def _ensure_sqlite_parent_exists(database_url: str) -> None:
    prefix = "sqlite+pysqlite:///"
    if not database_url.startswith(prefix):
        return

    raw_path = database_url.removeprefix(prefix)
    if raw_path == ":memory:":
        return

    db_path = Path(raw_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
