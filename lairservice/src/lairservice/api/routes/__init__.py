"""API 路由组装。

- `router`：顶层路由（/health、/assistant/invoke、/notes —— 早期 harness 入口）
- `api_router`：业务路由，统一挂 /api 前缀（与前端 mock 契约一致）
"""

from fastapi import APIRouter, Request

from lairservice.api.routes.auth import router as auth_router
from lairservice.api.routes.books import router as books_router
from lairservice.api.routes.ledger import router as ledger_router
from lairservice.api.routes.modules import (
    calendar_router,
    habits_router,
    notes_router,
    overview_router,
    todo_router,
)
from lairservice.api.schemas import (
    AssistantInvokeRequest,
    AssistantInvokeResponse,
    HealthResponse,
    NoteResponse,
)
from lairservice.modules.notes import NotesService
from lairservice.runtime.base import AssistantRuntime

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post("/assistant/invoke", response_model=AssistantInvokeResponse)
async def invoke_assistant(request: Request, payload: AssistantInvokeRequest) -> AssistantInvokeResponse:
    runtime: AssistantRuntime = request.app.state.assistant_runtime
    response = await runtime.invoke(
        message=payload.message,
        user_id=payload.user_id,
        session_id=payload.session_id,
    )
    return AssistantInvokeResponse(
        message=response.message,
        session_id=response.session_id,
        route=response.route,
    )


@router.get("/notes", response_model=list[NoteResponse])
async def list_notes(request: Request, user_id: str = "local-user") -> list[NoteResponse]:
    notes_service: NotesService = request.app.state.notes_service
    notes = notes_service.list_notes(user_id=user_id)
    return [NoteResponse(id=note.id, content=note.content or "") for note in notes]


api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(ledger_router)
api_router.include_router(books_router)
api_router.include_router(todo_router)
api_router.include_router(calendar_router)
api_router.include_router(notes_router)
api_router.include_router(habits_router)
api_router.include_router(overview_router)
