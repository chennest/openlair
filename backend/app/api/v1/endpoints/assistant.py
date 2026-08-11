"""/api/assistant 路由：AI 助手（会话 + SSE 流式对话 + 安全确认）。

SSE 事件行格式：`data: {json}\n\n`，事件类型见 services/assistant/events.py。
"""

import json

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import AssistantChatInput, AssistantConfirmInput
from app.core.envelope import ApiError, ok_response
from app.models.user import User
from app.services.assistant.events import AssistantEvent, ErrorEvent
from app.services.assistant.transcribe import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

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


@router.post("/transcribe")
async def transcribe(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    if suffix not in ALLOWED_EXTENSIONS:
        raise ApiError(400, "不支持的音频格式")
    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise ApiError(400, "音频文件不能超过 10MB")
    service = request.app.state.transcribe_service
    text = await service.transcribe_audio(audio_bytes=data, filename=file.filename or "audio.wav")
    return ok_response({"text": text}, "转写成功")


def _sse(event: AssistantEvent) -> str:
    return f"data: {json.dumps(event.model_dump(), ensure_ascii=False)}\n\n"
