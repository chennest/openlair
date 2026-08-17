"""AI 助手 runtime 抽象层：单一持久线程 + 多轮记忆 + 上下文自动压缩 + 安全确认。

聊天流转框架（transcript）：对话是一条平铺有序的 transcript，
每轮 = user → assistant（你）→ tool（工具执行结果）；tool 结果是聊天流的一等公民，
既持久化也回放进模型上下文（带 [工具结果] 前缀），压缩时整体摘要成事实。

- 只依赖 LoopEngine 协议（loop/base.py），不 import 具体框架；
- confirm 级工具被调用时 → 生成计划落库（AssistantPlan）→ 事件流带 confirm_request →
  用户确认后由 runtime 用「已确认的参数」直接落库（参数不再经过 LLM，防幻觉偏差）；
- 历史超预算时（token 估算）触发自动压缩：较早轮次摘要成检查点，近期原文保留；
- 工具只调 services，分层不变。
"""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.core.envelope import ApiError
from app.models.assistant import AssistantMessage, AssistantSession
from app.services import iso_z
from app.services.assistant.compaction import (
    COMPACTION_SYSTEM_PROMPT,
    TOOL_RESULT_PREFIX,
    checkpoint_message,
    estimate_tokens,
)
from app.services.assistant.events import (
    AssistantEvent,
    ConfirmRequestEvent,
    DoneEvent,
    ErrorEvent,
    MessageDeltaEvent,
)
from app.services.assistant.loop.base import LoopEngine, LoopMessage
from app.services.assistant.plans import PlanService
from app.services.assistant.tools.ledger import (
    LedgerPlan,
    build_ledger_tools,
    session_ctx,
    user_ctx,
)
from app.services.books import BookService
from app.services.ledger import LedgerService

logger = logging.getLogger(__name__)


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
4. 若上下文里已有「已记账」的工具结果，不要重复记同一笔；结合历史判断是否为新请求。
5. 回复简洁中文，复述计划后请用户确认。"""


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


_CANCEL_FOLLOWUP_SYSTEM = (
    "你是 OpenLair 的 AI 记账助手。用户刚才取消了一个记账计划。"
    "请用一句简洁自然的中文回应，包含："
    "1) 确认没有记这笔账；2) 复述被取消的内容（金额/分类）；"
    "3) 说明记账工具的作用（把用户的一句话变成一条流水，方便月底统计）；"
    "4) 询问是否需要修改金额或分类。"
    "不要道歉、不要长篇大论，一两句即可。"
)


def _cancel_followup_template(summary: str) -> str:
    """取消追问的确定性兜底（LLM 不可用时）。"""
    return f"好的，没记这笔「{summary}」。想改金额或分类的话直接说；记账工具会把它变成一条流水、方便月底统计。"


class AssistantRuntime:
    """AI 助手运行时：loop 之上的抽象封装（会话 / 多轮对话 / 自动压缩 / 安全确认）。"""

    def __init__(
        self,
        *,
        session_factory,
        books: BookService,
        ledger: LedgerService,
        plans: PlanService,
        engine: LoopEngine,
        llm_api_key: str,
        compact_threshold_tokens: int = 4000,
        retain_tokens: int = 1200,
    ) -> None:
        self._sf = session_factory
        self._books = books
        self._ledger = ledger
        self._plans = plans
        self._engine = engine
        self._llm_ready = bool(llm_api_key)
        self._compact_threshold = compact_threshold_tokens
        self._retain_tokens = retain_tokens
        self._tools = build_ledger_tools(books=books, ledger=ledger)

    # ---------- 会话（单一持久线程） ----------

    def create_session(self, *, user_id: int) -> dict:
        """幂等：每个用户一条持久线程，已存在则返回，否则新建。"""
        with self._sf() as s:
            sess = (
                s.query(AssistantSession)
                .filter_by(user_id=user_id)
                .order_by(AssistantSession.updated_at.desc())
                .first()
            )
            if sess is not None:
                return {"id": sess.id, "title": sess.title, "updatedAt": iso_z(sess.updated_at)}
            sess = AssistantSession(user_id=user_id, title="新对话")
            s.add(sess)
            s.commit()
            return {"id": sess.id, "title": sess.title, "updatedAt": iso_z(sess.created_at)}

    def list_sessions(self, *, user_id: int) -> list[dict]:
        """返回该用户的持久线程（有消息才显示；单一线程通常至多一条）。"""
        with self._sf() as s:
            has_msgs = exists().where(AssistantMessage.session_id == AssistantSession.id)
            rows = (
                s.query(AssistantSession)
                .filter(has_msgs)
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
                    "type": r.type,
                    "content": r.content,
                    "meta": r.meta,
                    "createdAt": iso_z(r.created_at),
                }
                for r in rows
            ]

    def delete_session(self, *, user_id: int, session_id: int) -> None:
        """删除会话及其全部消息，清理 DB 中的待确认计划。"""
        with self._sf() as s:
            self._require_session(s, user_id, session_id)
            s.query(AssistantMessage).filter_by(session_id=session_id).delete()
            s.query(AssistantSession).filter_by(id=session_id).delete()
            s.commit()
        self._plans.clear_for_session(user_id=user_id, session_id=session_id)

    # ---------- 对话（多轮） ----------

    async def chat(
        self, *, user_id: int, session_id: int | None, message: str
    ) -> AsyncIterator[AssistantEvent]:
        """流式执行一轮对话。事件经 SSE 转发给前端。
        session_id=None 时复用该用户的持久线程（无则新建）。"""
        text = (message or "").strip()
        if not text:
            yield ErrorEvent(message="消息不能为空")
            return

        with self._sf() as s:
            sess = self._get_or_create_session(s, user_id, session_id)
            session_id = sess.id
            # 首条消息作为会话标题
            if s.query(AssistantMessage).filter_by(session_id=session_id).count() == 0:
                sess.title = text[:20]
            s.add(AssistantMessage(session_id=session_id, role="user", content=text, type="text"))
            s.commit()

        if not self._llm_ready:
            yield ErrorEvent(message="AI 助手未配置（缺少 LLM_API_KEY），请先在 backend/.env 配置")
            yield DoneEvent(sessionId=session_id)
            return

        # 上下文自动压缩：历史超预算时，把较早轮次摘要成检查点
        await self._maybe_compact(session_id=session_id)

        history = self._build_history(session_id=session_id)
        books_text = "、".join(f"{b['name']}" for b in self._books.list(user_id=user_id))
        categories_text = "、".join(f"{c['name']}({c['type']})" for c in self._ledger.categories())

        u_token = user_ctx.set(user_id)
        s_token = session_ctx.set(session_id)
        chunks: list[str] = []
        plan_output: dict | None = None
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

        # 结构化输出为记账计划 → 先生成 plan 落库，再写 AI 消息带 meta（同一事务）
        plan_id: str | None = None
        plan_summary: str | None = None
        if plan_output and plan_output.get("action") == "record":
            args = {k: plan_output.get(k) for k in ("type", "amount", "category", "date", "book", "note")}
            plan_summary = _plan_summary(plan_output)
            plan_dict = self._plans.create(
                user_id=user_id,
                session_id=session_id,
                tool="LedgerPlan",
                args=args,
                summary=plan_summary,
            )
            plan_id = plan_dict["plan_id"]

        # 写 AI 消息（带 type 与 meta）
        with self._sf() as s:
            meta: dict | None = None
            msg_type = "text"
            if plan_id:
                meta = {"planId": plan_id, "tool": "LedgerPlan", "summary": plan_summary}
                msg_type = "confirm_request"
            msg = AssistantMessage(
                session_id=session_id,
                role="assistant",
                type=msg_type,
                content=assistant_text,
                meta=meta,
            )
            s.add(msg)
            sess = s.get(AssistantSession, session_id)
            if sess is not None:
                sess.updated_at = datetime.now(UTC)
            s.commit()

        if plan_id:
            yield ConfirmRequestEvent(planId=plan_id, tool="LedgerPlan", summary=plan_summary or "")
        yield DoneEvent(sessionId=session_id)

    # ---------- 历史构建与自动压缩 ----------

    def _build_history(self, *, session_id: int) -> list[LoopMessage]:
        """构建喂给模型的近期上下文：检查点摘要 + 未被压缩的消息（不含当前消息）。

        按聊天流转框架有序回放：user → assistant → tool（工具执行结果）。
        tool 结果加前缀，与「助手说的话」区分。
        """
        with self._sf() as s:
            sess = s.get(AssistantSession, session_id)
            history: list[LoopMessage] = []
            if sess is not None and sess.summary:
                history.append(LoopMessage(role="user", content=checkpoint_message(sess.summary)))
            boundary = (sess.summary_through_id or 0) if sess is not None else 0
            rows = (
                s.query(AssistantMessage)
                .filter_by(session_id=session_id)
                .filter(AssistantMessage.id > boundary)
                .order_by(AssistantMessage.id.asc())
                .all()
            )
            # 最后一条是刚写入的当前用户消息（由 prompt 参数传入），不进 history
            for r in rows[:-1]:
                if r.type == "tool_result":
                    history.append(LoopMessage(role="assistant", content=TOOL_RESULT_PREFIX + r.content))
                else:
                    history.append(LoopMessage(role=r.role, content=r.content))
            return history

    async def _maybe_compact(self, *, session_id: int) -> None:
        """历史 token 估算超阈值时，把较早轮次摘要成检查点（失败则降级，不阻塞本轮）。"""
        if not self._llm_ready:
            return
        try:
            with self._sf() as s:
                sess = s.get(AssistantSession, session_id)
                if sess is None:
                    return
                boundary = sess.summary_through_id or 0
                tail = (
                    s.query(AssistantMessage)
                    .filter_by(session_id=session_id)
                    .filter(AssistantMessage.id > boundary)
                    .order_by(AssistantMessage.id.asc())
                    .all()
                )
                total = estimate_tokens(sess.summary or "")
                for r in tail:
                    total += estimate_tokens(r.content)
                if total <= self._compact_threshold or len(tail) <= 1:
                    return

                # 从尾部往前保留近期原文，直到达到 retain 预算
                keep: list[AssistantMessage] = []
                keep_tokens = 0
                for r in reversed(tail):
                    t = estimate_tokens(r.content)
                    if keep and keep_tokens + t > self._retain_tokens:
                        break
                    keep.append(r)
                    keep_tokens += t
                keep.reverse()
                to_compact = tail[: len(tail) - len(keep)]
                if not to_compact:
                    return
                prior_summary = sess.summary
                cutoff_id = to_compact[-1].id
                to_summarize = [
                    LoopMessage(
                        role="assistant" if r.type == "tool_result" else r.role,
                        content=(TOOL_RESULT_PREFIX + r.content) if r.type == "tool_result" else r.content,
                    )
                    for r in to_compact
                ]

            summary = await self._summarize(to_summarize, prior_summary=prior_summary)

            with self._sf() as s:
                sess = s.get(AssistantSession, session_id)
                if sess is not None:
                    sess.summary = summary
                    sess.summary_through_id = cutoff_id
                    sess.updated_at = datetime.now(UTC)
                    s.commit()
        except Exception:
            # 压缩是尽力而为：失败保留原历史继续（对齐 harness「摘要失败保留最新表层」）
            logger.exception("assistant compaction failed; keeping original history")

    async def _summarize(self, messages: list[LoopMessage], *, prior_summary: str | None) -> str:
        """用一次独立的 LLM 调用把较早轮次摘要成检查点（原始消息仍在 DB 可回放）。"""
        history: list[LoopMessage] = []
        if prior_summary:
            history.append(LoopMessage(role="user", content=prior_summary))
        history.extend(messages)
        chunks: list[str] = []
        async for ev in self._engine.stream(
            system_prompt=COMPACTION_SYSTEM_PROMPT,
            tools=[],
            history=history,
            prompt="请基于以上对话历史生成压缩摘要（只输出摘要内容本身）。",
            output_schema=None,
        ):
            if ev.kind == "delta":
                chunks.append(ev.text)
        summary = "".join(chunks).strip()
        if not summary:
            raise ApiError(500, "上下文压缩失败：摘要为空")
        return summary

    # ---------- 安全确认 ----------

    async def confirm(self, *, user_id: int, plan_id: str, approved: bool) -> dict:
        """用户对待确认计划表态：approved=True 用已确认参数落库；False 取消并让 AI 追问。"""
        result = self._plans.confirm(user_id=user_id, plan_id=plan_id, approved=approved)
        # 追加工具执行结果消息（聊天流转框架里的 tool 段）
        self._append(
            session_id=result["session_id"],
            role="assistant",
            type="tool_result",
            content=result["message"],
            meta={
                "planId": plan_id,
                "kind": result["kind"],
                "summary": result.get("summary", ""),
                "result": result["message"],
            },
        )
        resp = {"ok": result["ok"], "message": result["message"]}
        if not approved:
            follow_up = await self._generate_cancel_followup(summary=result.get("summary", ""))
            self._append(
                session_id=result["session_id"],
                role="assistant",
                type="text",
                content=follow_up,
            )
            resp["followUp"] = follow_up
        return resp

    async def _generate_cancel_followup(self, *, summary: str) -> str:
        """取消后让 AI 追问：确认没记 + 复述被取消内容 + 一句工具用途 + 问要不要改。

        LLM 失败或无 key 时回退到确定性模板，保证取消永远有回应。
        """
        if self._llm_ready:
            try:
                chunks: list[str] = []
                async for ev in self._engine.stream(
                    system_prompt=_CANCEL_FOLLOWUP_SYSTEM,
                    tools=[],
                    history=[],
                    prompt=f"被取消的记账计划是：{summary}",
                    output_schema=None,
                ):
                    if ev.kind == "delta":
                        chunks.append(ev.text)
                text = "".join(chunks).strip()
                if text:
                    return text
            except Exception:
                logger.exception("cancel followup generation failed; using template")
        return _cancel_followup_template(summary)

    # ---------- 内部 ----------

    def _require_session(self, s: Session, user_id: int, session_id: int) -> AssistantSession:
        sess = s.get(AssistantSession, session_id)
        if sess is None or sess.user_id != user_id:
            raise ApiError(404, "会话不存在")
        return sess

    def _get_or_create_session(
        self, s: Session, user_id: int, session_id: int | None
    ) -> AssistantSession:
        """单一持久线程：显式 session_id 校验；None 则复用用户最近会话，无则新建。"""
        if session_id is not None:
            return self._require_session(s, user_id, session_id)
        sess = (
            s.query(AssistantSession)
            .filter_by(user_id=user_id)
            .order_by(AssistantSession.updated_at.desc())
            .first()
        )
        if sess is not None:
            return sess
        sess = AssistantSession(user_id=user_id, title="新对话")
        s.add(sess)
        s.flush()
        return sess

    def _append(
        self, session_id: int, content: str, *, role: str = "assistant",
        type: str = "text", meta: dict | None = None
    ) -> None:
        with self._sf() as s:
            s.add(
                AssistantMessage(
                    session_id=session_id,
                    role=role,
                    type=type,
                    content=content,
                    meta=meta,
                )
            )
            s.commit()
