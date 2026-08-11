"""AI 助手 runtime：统一事件模型（runtime → 前端 SSE 转发用）。

事件类型：
- message_delta   流式回复增量文本
- confirm_request 待确认计划（前端渲染确认卡片）
- done            一轮对话结束
- error           错误（LLM 未配置 / 会话异常等）
"""

from typing import Literal

from pydantic import BaseModel


class MessageDeltaEvent(BaseModel):
    type: Literal["message_delta"] = "message_delta"
    delta: str


class ConfirmRequestEvent(BaseModel):
    type: Literal["confirm_request"] = "confirm_request"
    planId: str
    tool: str
    summary: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    sessionId: int


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


AssistantEvent = MessageDeltaEvent | ConfirmRequestEvent | DoneEvent | ErrorEvent
