"""API 请求模型（字段名与前端契约一致：camelCase）。"""

from datetime import date as _date

from pydantic import BaseModel, Field


# ---------- 早期 harness 入口 ----------

class HealthResponse(BaseModel):
    status: str


class AssistantInvokeRequest(BaseModel):
    message: str = Field(min_length=1)
    user_id: str = Field(default="local-user", min_length=1)
    session_id: str = Field(default="default", min_length=1)


class AssistantInvokeResponse(BaseModel):
    message: str
    session_id: str
    route: str


class NoteResponse(BaseModel):
    id: int
    content: str


# ---------- auth ----------

class RegisterInput(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    email: str
    password: str = Field(min_length=6, max_length=64)


class LoginInput(BaseModel):
    email: str
    password: str


# ---------- ledger ----------

class CreateTransactionInput(BaseModel):
    type: str
    categoryId: int | None = None
    category: str | None = None  # 兼容：分类名
    amount: float
    date: _date | None = None
    note: str | None = None
    bookId: int | None = None


class UpdateTransactionInput(BaseModel):
    type: str | None = None
    categoryId: int | None = None
    amount: float | None = None
    date: _date | None = None
    note: str | None = None
    bookId: int | None = None


class UpdateBudgetInput(BaseModel):
    bookId: int | None = None
    amount: float


# ---------- books ----------

class CreateBookInput(BaseModel):
    name: str = Field(default="共享账本", max_length=60)
    type: str = "personal"


class AddMemberInput(BaseModel):
    userId: int | None = None
    name: str | None = None


# ---------- todo ----------

class CreateTodoInput(BaseModel):
    text: str = Field(min_length=1, max_length=200)
    quadrant: str | None = None
    due: str | None = None


class UpdateTodoInput(BaseModel):
    text: str | None = None
    quadrant: str | None = None
    done: bool | None = None
    due: str | None = None


# ---------- calendar ----------

class CreateEventInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: _date | None = None
    time: str | None = None
    location: str | None = None


class UpdateEventInput(BaseModel):
    title: str | None = None
    date: _date | None = None
    time: str | None = None
    location: str | None = None
    done: bool | None = None


# ---------- notes ----------

class CreateNoteInput(BaseModel):
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None


class UpdateNoteInput(BaseModel):
    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None


# ---------- habits ----------

class CreateHabitInput(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class UpdateHabitInput(BaseModel):
    name: str | None = None
    streak: int | None = None
    done: bool | None = None
    week: list[bool] | None = None


# ---------- assistant（AI 助手） ----------

class AssistantChatInput(BaseModel):
    sessionId: int | None = None  # null=自动创建新会话
    message: str = Field(min_length=1, max_length=2000)


class AssistantConfirmInput(BaseModel):
    planId: str = Field(min_length=1)
    approved: bool
