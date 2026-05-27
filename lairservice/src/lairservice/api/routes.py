from fastapi import APIRouter, Request

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
    return [NoteResponse(id=note.id, content=note.content) for note in notes]
