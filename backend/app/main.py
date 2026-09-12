from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.system import instrumentator, router as system_router
from app.api.v1.router import v1_router
from app.core.config import get_settings
from app.core.envelope import register_envelope_handlers
from app.db.session import create_database_engine, create_session_factory, init_database
from app.repositories.api_keys import ApiKeyRepository
from app.repositories.books import BookRepository
from app.repositories.days import DayRepository
from app.repositories.events import EventRepository
from app.repositories.habits import HabitRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.notes import NoteRepository
from app.repositories.settings import SettingRepository
from app.repositories.todo import TodoRepository
from app.repositories.tokens import TokenRepository
from app.repositories.users import UserRepository
from app.seed import seed
from app.services.api_keys import ApiKeyService
from app.services.assistant.loop.pydantic_ai import PydanticAIEngine
from app.services.assistant.plans import PlanService
from app.services.assistant.runtime import AssistantRuntime
from app.services.assistant.transcribe import create_transcriber
from app.services.snap import SnapParser
from app.services.auth import AuthService
from app.services.books import BookService
from app.services.ledger import LedgerService
from app.services.modules import (
    DayService,
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
    api_key_repo = ApiKeyRepository(session_factory)
    book_repo = BookRepository(session_factory)
    ledger_repo = LedgerRepository(session_factory)
    todo_repo = TodoRepository(session_factory)
    event_repo = EventRepository(session_factory)
    note_repo = NoteRepository(session_factory)
    habit_repo = HabitRepository(session_factory)
    day_repo = DayRepository(session_factory)
    setting_repo = SettingRepository(session_factory)
    app.state.setting_repo = setting_repo

    # ---------- 服务（业务逻辑层） ----------
    app.state.auth_service = AuthService(user_repo, token_repo, setting_repo)
    app.state.api_key_service = ApiKeyService(api_key_repo)
    app.state.ledger_service = LedgerService(ledger_repo, user_repo, book_repo)
    app.state.book_service = BookService(book_repo, user_repo)
    app.state.todo_service = TodoService(todo_repo)
    app.state.event_service = EventService(event_repo)
    app.state.note_service = NoteService(note_repo)
    app.state.habit_service = HabitService(habit_repo)
    app.state.day_service = DayService(day_repo)
    app.state.overview_service = OverviewService(
        ledger=ledger_repo, todo=todo_repo, events=event_repo, habits=habit_repo, books=book_repo
    )

    # ---------- AI 助手 runtime（loop 之上的抽象封装） ----------
    app.state.assistant_runtime = AssistantRuntime(
        session_factory=session_factory,
        books=app.state.book_service,
        ledger=app.state.ledger_service,
        plans=PlanService(
            session_factory=session_factory,
            ledger=app.state.ledger_service,
            books=app.state.book_service,
        ),
        engine=PydanticAIEngine(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        ),
        llm_api_key=settings.llm_api_key,
        compact_threshold_tokens=settings.llm_compact_threshold_tokens,
        retain_tokens=settings.llm_compact_retain_tokens,
    )

    # ---------- 语音转写服务 ----------
    app.state.transcribe_service = create_transcriber(
        engine=settings.transcribe_engine,
        dashscope_base_url=settings.transcribe_base_url,
        dashscope_api_key=settings.transcribe_api_key,
        dashscope_model=settings.transcribe_model,
        openai_base_url=settings.transcribe_openai_base_url,
        openai_api_key=settings.transcribe_openai_api_key,
        openai_model=settings.transcribe_model,
    )

    # ---------- 截图识别服务（视觉多模态；SNAP_* 缺省回退 LLM_*） ----------
    app.state.snap_parser = SnapParser(
        base_url=settings.snap_base_url or settings.llm_base_url,
        api_key=settings.snap_api_key or settings.llm_api_key,
        model=settings.snap_model,
    )

    # ---------- 鉴权依赖所需仓储 ----------
    app.state.user_repository = user_repo
    app.state.token_repository = token_repo
    app.state.api_key_repository = api_key_repo

    # ---------- 系统路由（K8s 探针 + Prometheus 指标）----------
    # session_factory 挂到 app.state，供 /healthz/ready 就绪探针检查 DB 连通
    app.state.session_factory = session_factory
    app.include_router(system_router)
    # Prometheus 指标：自动采集全部 HTTP 路由（排除探针自身路径），并暴露 /metrics
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    app.include_router(v1_router)
    return app


app = create_app()
