"""AI 助手工具：记账域工具。

约定：
- 查询工具 = async (**kwargs) -> str，参数类型注解即 LLM 工具 schema（pydantic-ai 推断）。
- 记账不走工具调用，走「结构化输出」（LedgerPlan）：LLM 必须以 schema 输出记账计划，
  用户确认后由 runtime 落库 —— 比工具调用可靠（JSON schema 强制，防模型文本模拟）。
- 当前用户/会话通过 contextvar 注入（runtime.chat 设置），函数签名保持纯业务、零框架依赖。
- 只调 services（BookService / LedgerService），不碰 repositories/DB —— 保持分层不变。
"""

import contextvars
import re
from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, Field

from app.core.envelope import ApiError
from app.services.assistant.loop.base import LoopTool
from app.services.books import BookService
from app.services.ledger import LedgerService

# 当前用户 / 会话上下文（runtime.chat 进入时 set，工具执行时读取）
user_ctx: contextvars.ContextVar[int] = contextvars.ContextVar("assistant_user_id", default=0)
session_ctx: contextvars.ContextVar[int] = contextvars.ContextVar("assistant_session_id", default=0)


class LedgerPlan(BaseModel):
    """AI 记账计划：LLM 的结构化输出（记账唯一入口），用户确认后执行。

    action=record 时必须提供 amount；action=skip 表示本轮不是记账请求（纯对话/查询）。
    """

    action: Literal["record", "skip"] = Field(
        description="record=用户要求记账；skip=不是记账请求（闲聊/查询），置为 skip"
    )
    type: Literal["支出", "收入"] = "支出"
    amount: float | None = Field(default=None, gt=0, description="金额（元，正数）")
    category: str | None = Field(default=None, description="分类名（从可用分类列表中选择）")
    date: str | None = Field(default=None, description="日期表达：今天/昨天/前天/N天前/YYYY-MM-DD")
    book: str | None = Field(default=None, description="账本名（从可用账本列表中选择）")
    note: str | None = Field(default=None, description="备注")


def _resolve_date(value: str | None) -> date | None:
    """解析 LLM 给出的日期表达（YYYY-MM-DD / 今天 / 昨天 / N天前 / 上周X 等）。

    超出合理范围（未来日期、解析失败）返回 None，由确认环节兜底。
    """
    if not value:
        return None
    today = datetime.now().date()
    text = value.strip()
    try:
        return date.fromisoformat(text)
    except ValueError:
        pass
    if text == "今天":
        return today
    if text == "昨天":
        return today - timedelta(days=1)
    if text == "前天":
        return today - timedelta(days=2)
    m = re.match(r"^(\d+)\s*天前$", text)
    if m:
        days = int(m.group(1))
        return today - timedelta(days=days) if 0 <= days <= 365 else None
    m = re.match(r"^(\d{1,2})月(\d{1,2})[日号]?$", text)
    if m:
        try:
            d = date(today.year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
        return d if d <= today else None
    return None


def build_ledger_tools(*, books: BookService, ledger: LedgerService) -> list[LoopTool]:
    """构建记账域查询工具（记账走 LedgerPlan 结构化输出，不在此注册）。"""

    async def list_books(book_name: str | None = None) -> str:
        """列出当前用户的账本（名称 + id + 类型）。可用 book_name 过滤。"""
        rows = books.list(user_id=user_ctx.get())
        if not rows:
            return "（当前没有账本，请先在前端创建账本）"
        if book_name:
            rows = [b for b in rows if book_name in b["name"]]
        if not rows:
            return "（没有匹配的账本）"
        return "\n".join(f"{b['name']} (id={b['id']}, {b['type']})" for b in rows)

    async def list_categories(type: str | None = None) -> str:
        """列出记账分类（名称 + id + 收支类型）。type 可传「收入」或「支出」过滤。"""
        rows = ledger.categories(type)
        if not rows:
            return "（没有分类）"
        return "\n".join(f"{c['name']} (id={c['id']}, {c['type']})" for c in rows)

    return [
        LoopTool(name="list_books", description="列出当前用户的记账账本", fn=list_books),
        LoopTool(name="list_categories", description="列出记账分类", fn=list_categories),
    ]


def execute_create_plan(*, ledger: LedgerService, books: BookService, args: dict, user_id: int) -> str:
    """用户确认后执行记账计划（args 为 LLM 结构化输出、用户已确认的参数）。返回落库结果文本。"""
    book_id: int | None = None
    book_name = args.get("book")
    if book_name:
        matched = next((b for b in books.list(user_id=user_id) if b["name"] == book_name), None)
        book_id = matched["id"] if matched else None

    cid: int | None = None
    category_name = args.get("category")
    if category_name:
        matched = next((c for c in ledger.categories() if c["name"] == category_name), None)
        cid = matched["id"] if matched else None

    result = ledger.create(
        user_id=user_id,
        type=args.get("type") or "支出",
        category_id=cid,
        amount=float(args.get("amount") or 0),
        date=_resolve_date(args.get("date")),
        note=(args.get("note") or "").strip(),
        book_id=book_id,
    )
    item = result["item"]
    return f"已记账：{item['type']} {item['amount']:.2f} 元 · {item['category']} · {item['date']}"
