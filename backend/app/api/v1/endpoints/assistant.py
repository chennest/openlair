"""/api/assistant 路由：AI 助手（会话 + SSE 流式对话 + 安全确认）。

SSE 事件行格式：`data: {json}\n\n`，事件类型见 services/assistant/events.py。
"""

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import AssistantChatInput, AssistantConfirmInput
from app.core.envelope import ApiError, ok_response
from app.models.user import User
from app.services.assistant.events import AssistantEvent, ErrorEvent

router = APIRouter(prefix="/assistant", tags=["assistant"])


def _runtime(request: Request):
    return request.app.state.assistant_runtime


@router.post("/sessions")
async def create_session(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(_runtime(request).create_session(user_id=user.id), "创建成功")


@router.get("/sessions")
async def list_sessions(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(_runtime(request).list_sessions(user_id=user.id))


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    request: Request, session_id: int, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(_runtime(request).get_messages(user_id=user.id, session_id=session_id))


@router.delete("/sessions/{session_id}")
async def delete_session(
    request: Request, session_id: int, user: User = Depends(get_current_user)
) -> dict:
    _runtime(request).delete_session(user_id=user.id, session_id=session_id)
    return ok_response({"ok": True}, "已删除")


@router.post("/chat")
async def chat(
    request: Request, payload: AssistantChatInput, user: User = Depends(get_current_user)
) -> StreamingResponse:
    runtime = _runtime(request)

    async def event_stream():
        try:
            async for event in runtime.chat(user_id=user.id, session_id=payload.sessionId, message=payload.message):
                yield _sse(event)
        except ApiError as e:
            yield _sse(ErrorEvent(message=e.message))

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@router.post("/confirm")
async def confirm(
    request: Request, payload: AssistantConfirmInput, user: User = Depends(get_current_user)
) -> dict:
    result = _runtime(request).confirm(user_id=user.id, plan_id=payload.planId, approved=payload.approved)
    return ok_response(result, result["message"])


def _sse(event: AssistantEvent) -> str:
    return f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
