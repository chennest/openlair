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


# ---------- api keys ----------

class CreateApiKeyInput(BaseModel):
    name: str = Field(min_length=1, max_length=30)


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


class CategoryCreateInput(BaseModel):
    name: str = Field(min_length=1, max_length=20)
    type: str  # 支出 | 收入


class CategoryUpdateInput(BaseModel):
    name: str = Field(min_length=1, max_length=20)


# ---------- books ----------

class CreateBookInput(BaseModel):
    name: str = Field(default="共享账本", max_length=60)
    type: str = "personal"


class AddMemberInput(BaseModel):
    userId: int | None = None
    name: str | None = None


class JoinBookInput(BaseModel):
    code: str = Field(min_length=1, max_length=32)


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


# ---------- days（倒数日 / 纪念日） ----------

class CreateDayInput(BaseModel):
    title: str = Field(min_length=1, max_length=60)
    date: _date
    emoji: str = Field(default="", max_length=8)
    repeat: str = "once"  # once 一次性 / yearly 每年 / monthly 每月
    pinned: bool = False


class UpdateDayInput(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=60)
    date: _date | None = None
    emoji: str | None = Field(default=None, max_length=8)
    repeat: str | None = None
    pinned: bool | None = None


# ---------- assistant（AI 助手） ----------

class AssistantChatInput(BaseModel):
    sessionId: int | None = None  # null=自动创建新会话
    message: str = Field(min_length=1, max_length=2000)


class AssistantConfirmInput(BaseModel):
    planId: str = Field(min_length=1)
    approved: bool


# ---------- vocab（词汇打字练习） ----------

class StartSessionInput(BaseModel):
    bookId: int = 0  # source=wrong/collect 时忽略，可为 0
    mode: str = "follow"  # follow 跟打 / dictation 听写 / self_test 自测 / spell 默写
    source: str = "book"  # book 词书排课 / wrong 错词本 / collect 收藏复习
    newLimit: int | None = Field(default=None, ge=0, le=100)  # 不传=按每日目标剩余量发新词
    reviewLimit: int | None = Field(default=None, ge=0, le=100)  # 不传=按每日复习目标剩余量发复习
    tzOffset: int = Field(default=0, ge=-840, le=840)  # 本地相对 UTC 分钟差，用于折算「今天」边界


class UpdateDailyGoalInput(BaseModel):
    """/daily-goal 的请求体：两个字段都可选，只更新出现的字段。

    区间（1-100）刻意不在 schema 上校验：越界要返回统一信封的 400 + 中文提示，
    而不是 FastAPI 默认的 422 裸 {"detail":[...]}（那个形状被 laircli 依赖，不能改）。
    """

    newTarget: int | None = None  # 每日新词目标
    reviewTarget: int | None = None  # 每日复习目标


class SubmitAnswerInput(BaseModel):
    wordId: int
    correct: bool
    wrongTimes: int = Field(default=0, ge=0, le=100)
    durationMs: int = Field(default=0, ge=0)
    # 本地相对 UTC 的分钟差（东区为正）。未掌握的词要压到「次日」再复习，
    # 没有它就不知道用户的「次日零点」在哪（UTC+8 用户会被算到当天 08:00）。
    tzOffset: int = Field(default=0, ge=-840, le=840)


class FinishSessionInput(BaseModel):
    durationSec: int = Field(default=0, ge=0)


class UpdateVocabProgressInput(BaseModel):
    status: str | None = None  # learning / mastered
    collected: bool | None = None
    dismissWrong: bool | None = None  # true=移出错词本


class ImportBooksInput(BaseModel):
    name: str = Field(default="", max_length=100)  # 留空时 Anki #deck 头可自动命名
    scope: str = "user"  # system 系统级（仅站长，人人可见）/ user 用户级（仅本人）
    lang: str = Field(default="en", max_length=10)
    text: str = Field(min_length=1)  # Anki 导出文本 / ECDICT CSV / 简单行格式（每行一个单词，可选释义）
