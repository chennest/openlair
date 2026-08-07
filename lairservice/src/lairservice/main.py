from pathlib import Path
import os

from fastapi import FastAPI
from sqlalchemy.orm import Session

from lairservice.api.routes import api_router, router
from lairservice.core.envelope import register_envelope_handlers
from lairservice.db.session import create_database_engine, create_session_factory, init_database
from lairservice.models.gateway import ModelGateway, create_model_gateway_from_config
from lairservice.modules.notes import NotesRepository, NotesService
from lairservice.repositories.books import BookRepository
from lairservice.repositories.events import EventRepository
from lairservice.repositories.habits import HabitRepository
from lairservice.repositories.ledger import LedgerRepository
from lairservice.repositories.notes import NoteRepository
from lairservice.repositories.todo import TodoRepository
from lairservice.repositories.tokens import TokenRepository
from lairservice.repositories.users import UserRepository
from lairservice.runtime.langgraph_runtime import LangGraphAssistantRuntime
from lairservice.seed import seed
from lairservice.services.auth import AuthService
from lairservice.services.books import BookService
from lairservice.services.ledger import LedgerService
from lairservice.services.modules import (
    EventService,
    HabitService,
    NoteService,
    OverviewService,
    TodoService,
)


def create_app(
    database_url: str = "sqlite+pysqlite:///./data/lair.db",
    model_config_path: str | Path | None = None,
    model_gateway: ModelGateway | None = None,
) -> FastAPI:
    app = FastAPI(title="Lair Service", version="0.1.0")
    register_envelope_handlers(app)

    engine = create_database_engine(database_url)
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
    app.state.ledger_service = LedgerService(ledger_repo, user_repo)
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

    # ---------- agent harness（既有能力，保持不变） ----------
    notes_service = NotesService(NotesRepository(session_factory))
    app.state.notes_service = notes_service
    configured_path = model_config_path or os.environ.get("OPENLAIR_CONFIG")
    app.state.model_gateway = model_gateway or create_model_gateway_from_config(configured_path)
    app.state.assistant_runtime = LangGraphAssistantRuntime(model_gateway=app.state.model_gateway, workspace_path=".")

    app.include_router(router)
    app.include_router(api_router)
    return app


app = create_app()
