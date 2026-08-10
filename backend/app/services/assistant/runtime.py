"""AI 助手 runtime 抽象层：会话管理 + 对话执行 + 安全确认。

- 只依赖 LoopEngine 协议（loop/base.py），不 import 具体框架；
- confirm 级工具被调用时 → 生成 PendingPlan（内存态）→ 事件流带 confirm_request →
  用户确认后由 runtime 用「已确认的参数」直接落库（参数不再经过 LLM，防幻觉偏差）；
- 工具只调 services，分层不变。
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.envelope import ApiError
from app.models.assistant import AssistantMessage, AssistantSession
from app.services import iso_z
from app.services.assistant.events import (
    AssistantEvent,
    ConfirmRequestEvent,
    DoneEvent,
    ErrorEvent,
    MessageDeltaEvent,
)
from app.services.assistant.loop.base import LoopEngine, LoopMessage
from app.services.assistant.safety import PendingPlan, SafetyManager
from app.services.assistant.tools.ledger import (
    LedgerPlan,
    build_ledger_tools,
    execute_create_plan,
    session_ctx,
    user_ctx,
)
from app.services.books import BookService
from app.services.ledger import LedgerService

def _build_system_prompt(*, books_text: str, categories_text: str) -> str:
    """system prompt：注入今天的真实日期 + 可用账本/分类（防幻觉、免工具调用）。"""
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""你是 OpenLair 的 AI 记账助手，帮助用户用一句话完成记账。今天是{today}。

可用账本：{books_text or '（无）'}
可用分类：{categories_text or '（无）'}

规则：
1. 用户要求记账时，必须输出「记账计划」JSON（action=record，填写金额/分类/日期/账本/备注）。
   账本/分类只能从上面的「可用列表」中选择名称；账本未指定时用第一个账本；分类未指定时留空。
   不要向用户反问账本或分类（除非用户明确问）。
2. 非记账请求（闲聊/查询）输出 action=skip 即可。
3. 金额提取纯数字；「花了/支出」为支出，「收到/收入」为收入；日期用「今天/昨天/YYYY-MM-DD」，
   今天是{today}，未来日期不采用。
4. 回复简洁中文，复述计划后请用户确认。"""


_HISTORY_LIMIT = 20


def _plan_summary(args: dict) -> str:
    """把待确认计划的参数格式化成人类可读摘要（前端确认卡片展示）。"""
    parts = [f"{args.get('type') or '支出'} {float(args.get('amount') or 0):.2f} 元"]
    if args.get("category"):
        parts.append(f"分类 {args['category']}")
    if args.get("date"):
        parts.append(f"日期 {args['date']}")
    if args.get("book"):
        parts.append(f"账本 {args['book']}")
    if args.get("note"):
        parts.append(f"备注 {args['note']}")
    return " · ".join(parts)


class AssistantRuntime:
    """AI 助手运行时：loop 之上的抽象封装（会话 / 对话 / 安全确认）。"""

    def __init__(
        self,
        *,
        session_factory,
        books: BookService,
        ledger: LedgerService,
        safety: SafetyManager,
        engine: LoopEngine,
        llm_api_key: str,
    ) -> None:
        self._sf = session_factory
        self._books = books
        self._ledger = ledger
        self._safety = safety
        self._engine = engine
        self._llm_ready = bool(llm_api_key)
        self._tools = build_ledger_tools(books=books, ledger=ledger)

    # ---------- 会话 ----------

    def create_session(self, *, user_id: int) -> dict:
        with self._sf() as s:
            sess = AssistantSession(user_id=user_id, title="新会话")
            s.add(sess)
            s.commit()
            return {"id": sess.id, "title": sess.title}

    def list_sessions(self, *, user_id: int) -> list[dict]:
        with self._sf() as s:
            rows = (
                s.query(AssistantSession)
                .filter_by(user_id=user_id)
                .order_by(AssistantSession.updated_at.desc())
                .all()
            )
            return [
                {"id": r.id, "title": r.title, "updatedAt": iso_z(r.updated_at)} for r in rows
            ]

    def get_messages(self, *, user_id: int, session_id: int) -> list[dict]:
        with self._sf() as s:
            self._require_session(s, user_id, session_id)
            rows = (
                s.query(AssistantMessage)
                .filter_by(session_id=session_id)
                .order_by(AssistantMessage.id.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "role": r.role,
                    "content": r.content,
                    "meta": r.meta,
                    "createdAt": iso_z(r.created_at),
                }
                for r in rows
            ]

    # ---------- 对话 ----------

    async def chat(
        self, *, user_id: int, session_id: int, message: str
    ) -> AsyncIterator[AssistantEvent]:
        """流式执行一轮对话。事件经 SSE 转发给前端。"""
        text = (message or "").strip()
        if not text:
            yield ErrorEvent(message="消息不能为空")
            return

        with self._sf() as s:
            sess = self._require_session(s, user_id, session_id)
            # 先查历史（不含本条新消息），再插入 —— 否则 history+prompt 会重复
            history = [
                LoopMessage(role=m.role, content=m.content)
                for m in (
                    s.query(AssistantMessage)
                    .filter_by(session_id=session_id)
                    .order_by(AssistantMessage.id.desc())
                    .limit(_HISTORY_LIMIT)
                    .all()
                )
            ][::-1]
            if not history:
                sess.title = text[:20]
            s.add(AssistantMessage(session_id=session_id, role="user", content=text))
            s.commit()

        if not self._llm_ready:
            yield ErrorEvent(message="AI 助手未配置（缺少 LLM_API_KEY），请先在 backend/.env 配置")
            yield DoneEvent(sessionId=session_id)
            return

        u_token = user_ctx.set(user_id)
        s_token = session_ctx.set(session_id)
        chunks: list[str] = []
        plan_output: dict | None = None
        # 可用账本/分类注入 prompt（免工具调用，单轮 JSON 输出）
        books_text = "、".join(f"{b['name']}" for b in self._books.list(user_id=user_id))
        categories_text = "、".join(f"{c['name']}({c['type']})" for c in self._ledger.categories())
        try:
            async for ev in self._engine.stream(
                system_prompt=_build_system_prompt(
                    books_text=books_text, categories_text=categories_text
                ),
                tools=[],
                history=history,
                prompt=text,
                output_schema=LedgerPlan,
            ):
                if ev.kind == "delta":
                    chunks.append(ev.text)
                    yield MessageDeltaEvent(delta=ev.text)
                elif ev.kind == "done":
                    plan_output = ev.output
        finally:
            user_ctx.reset(u_token)
            session_ctx.reset(s_token)

        assistant_text = "".join(chunks).strip() or "（无回复）"
        with self._sf() as s:
            msg = AssistantMessage(session_id=session_id, role="assistant", content=assistant_text)
            s.add(msg)
            sess = s.get(AssistantSession, session_id)
            if sess is not None:
                sess.updated_at = datetime.now(UTC)
            s.commit()

        # 结构化输出为记账计划 → 生成待确认计划（用户确认后落库）
        if plan_output and plan_output.get("action") == "record":
            plan_id = uuid.uuid4().hex[:10]
            self._safety.add(
                PendingPlan(
                    plan_id=plan_id,
                    user_id=user_id,
                    session_id=session_id,
                    tool="LedgerPlan",
                    args={k: plan_output.get(k) for k in ("type", "amount", "category", "date", "book", "note")},
                    summary=_plan_summary(plan_output),
                )
            )
            yield ConfirmRequestEvent(planId=plan_id, tool="LedgerPlan", summary=_plan_summary(plan_output))
        yield DoneEvent(sessionId=session_id)

    # ---------- 安全确认 ----------

    def confirm(self, *, user_id: int, plan_id: str, approved: bool) -> dict:
        """用户对待确认计划表态：approved=True 用已确认参数落库，False 取消。"""
        plan = self._safety.pop(plan_id, user_id)
        if plan is None:
            raise ApiError(404, "计划不存在或已过期，请重新说一遍")
        if not approved:
            self._append(plan.session_id, "已取消本次操作")
            return {"ok": True, "message": "已取消"}
        try:
            text = execute_create_plan(
                ledger=self._ledger, books=self._books, args=plan.args, user_id=user_id
            )
        except ApiError as e:
            self._append(plan.session_id, f"记账失败：{e.message}")
            return {"ok": False, "message": f"记账失败：{e.message}"}
        self._append(plan.session_id, text, meta={"kind": "executed"})
        return {"ok": True, "message": text}

    # ---------- 内部 ----------

    def _require_session(self, s: Session, user_id: int, session_id: int) -> AssistantSession:
        sess = s.get(AssistantSession, session_id)
        if sess is None or sess.user_id != user_id:
            raise ApiError(404, "会话不存在")
        return sess

    def _append(self, session_id: int, content: str, *, meta: dict | None = None) -> None:
        with self._sf() as s:
            s.add(AssistantMessage(session_id=session_id, role="assistant", content=content, meta=meta))
            s.commit()
