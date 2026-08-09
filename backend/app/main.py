from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.envelope import register_envelope_handlers
from app.db.session import create_database_engine, create_session_factory, init_database
from app.repositories.books import BookRepository
from app.repositories.events import EventRepository
from app.repositories.habits import HabitRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.notes import NoteRepository
from app.repositories.todo import TodoRepository
from app.repositories.tokens import TokenRepository
from app.repositories.users import UserRepository
from app.seed import seed
from app.services.auth import AuthService
from app.services.books import BookService
from app.services.ledger import LedgerService
from app.services.modules import (
    EventService,
    HabitService,
    NoteService,
    OverviewService,
    TodoService,
)

# 数据库连接串：环境变量 → 项目 .env → 默认 SQLite（见 .env.example）
DEFAULT_DATABASE_URL = get_settings().database_url


def create_app(
    database_url: str | None = None,
    model_config_path: str | Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Lair Service", version="0.1.0")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_envelope_handlers(app)

    engine = create_database_engine(database_url or DEFAULT_DATABASE_URL)
    init_database(engine)
    session_factory = create_session_factory(engine)

    # 幂等 seed：测试账号 + 演示数据
    with session_factory() as session:
        seed(session)

    # ---------- 仓储 ----------
    user_repo = UserRepository(session_factory)
    token_repo = TokenRepository(session_factory)
    book_repo = BookRepository(session_factory)
    ledger_repo = LedgerRepository(session_factory)
    todo_repo = TodoRepository(session_factory)
    event_repo = EventRepository(session_factory)
    note_repo = NoteRepository(session_factory)
    habit_repo = HabitRepository(session_factory)

    # ---------- 服务（业务逻辑层） ----------
    app.state.auth_service = AuthService(user_repo, token_repo)
    app.state.ledger_service = LedgerService(ledger_repo, user_repo, book_repo)
    app.state.book_service = BookService(book_repo, user_repo)
    app.state.todo_service = TodoService(todo_repo)
    app.state.event_service = EventService(event_repo)
    app.state.note_service = NoteService(note_repo)
    app.state.habit_service = HabitService(habit_repo)
    app.state.overview_service = OverviewService(
        ledger=ledger_repo, todo=todo_repo, events=event_repo, habits=habit_repo
    )

    # ---------- 鉴权依赖所需仓储 ----------
    app.state.user_repository = user_repo
    app.state.token_repository = token_repo

    # 健康检查（K8s 探针用，不依赖业务服务）
    @app.get("/health", tags=["system"])
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(v1_router)
    return app


app = create_app()
