"""AI 助手：计划执行日志持久化服务（替代内存态 SafetyManager）。

- 计划状态机：pending → executed | cancelled | failed
- 按 plan_id + user_id 隔离，防越权确认
- 确认后写入 result 与 executed_at，供审计与回传 AI
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.envelope import ApiError
from app.models.assistant import AssistantPlan
from app.services.assistant.tools.ledger import _resolve_date, execute_create_plan
from app.services.books import BookService
from app.services.ledger import LedgerService


class PlanService:
    """计划执行日志 DB 持久化服务（替换内存 SafetyManager）。"""

    def __init__(
        self,
        *,
        session_factory,
        ledger: LedgerService,
        books: BookService,
    ) -> None:
        self._sf = session_factory
        self._ledger = ledger
        self._books = books

    # ---------- CRUD ----------

    def create(
        self, *, user_id: int, session_id: int, tool: str, args: dict, summary: str
    ) -> dict:
        """创建一条待确认计划（status=pending），返回 plan dict。"""
        plan_id = uuid.uuid4().hex[:10]
        with self._sf() as s:
            plan = AssistantPlan(
                plan_id=plan_id,
                user_id=user_id,
                session_id=session_id,
                tool=tool,
                args=args,
                summary=summary,
                status="pending",
            )
            s.add(plan)
            s.commit()
            return {
                "plan_id": plan_id,
                "summary": summary,
                "status": "pending",
                "session_id": session_id,
            }

    def get(self, *, user_id: int, plan_id: str) -> AssistantPlan | None:
        """按 plan_id + user_id 查计划（越权/不存在返回 None）。"""
        with self._sf() as s:
            return (
                s.query(AssistantPlan)
                .filter_by(plan_id=plan_id, user_id=user_id)
                .first()
            )

    def confirm(self, *, user_id: int, plan_id: str, approved: bool) -> dict:
        """用户对待确认计划表态：approved=True 执行落库，False 取消。

        返回 dict 含 ok / message / kind / session_id / summary，
        供 runtime 追加工具结果消息。
        """
        with self._sf() as s:
            plan = (
                s.query(AssistantPlan)
                .filter_by(plan_id=plan_id, user_id=user_id)
                .first()
            )
            if plan is None:
                raise ApiError(404, "计划不存在或已过期，请重新说一遍")
            if plan.status != "pending":
                raise ApiError(404, "计划不存在或已过期，请重新说一遍")

            if not approved:
                plan.status = "cancelled"
                plan.executed_at = datetime.now(UTC)
                s.commit()
                return {
                    "ok": True,
                    "message": "已取消",
                    "kind": "cancelled",
                    "session_id": plan.session_id,
                    "summary": plan.summary,
                }

            # approved=True：执行记账
            try:
                text = execute_create_plan(
                    ledger=self._ledger,
                    books=self._books,
                    args=plan.args,
                    user_id=user_id,
                )
                # 获取 transaction id：直接从 ledger.create 无法在此拿到，
                # 但 execute_create_plan 内部调了 ledger.create 且返回文本。
                # 我们从 args 重新调用 ledger.create 一次以捕获 id 或接受只用文本。
                # 为了与现有测试一致，复用 execute_create_plan 的返回值作为 message。
                plan.status = "executed"
                plan.result = {"message": text}
                plan.executed_at = datetime.now(UTC)
                s.commit()
                return {
                    "ok": True,
                    "message": text,
                    "kind": "executed",
                    "session_id": plan.session_id,
                    "summary": plan.summary,
                }
            except ApiError as e:
                plan.status = "failed"
                plan.result = {"message": e.message}
                plan.executed_at = datetime.now(UTC)
                s.commit()
                return {
                    "ok": False,
                    "message": f"记账失败：{e.message}",
                    "kind": "failed",
                    "session_id": plan.session_id,
                    "summary": plan.summary,
                }

    def clear_for_session(self, *, user_id: int, session_id: int) -> None:
        """删除该会话的全部计划（delete_session 时调）。"""
        with self._sf() as s:
            s.query(AssistantPlan).filter_by(
                user_id=user_id, session_id=session_id
            ).delete()
            s.commit()

    def recent_result(
        self, *, user_id: int, session_id: int, limit: int = 1
    ) -> list[dict]:
        """返回该会话最近非 pending 计划的 {kind, summary, result}（按 executed_at desc）。"""
        with self._sf() as s:
            rows = (
                s.query(AssistantPlan)
                .filter_by(user_id=user_id, session_id=session_id)
                .filter(AssistantPlan.status != "pending")
                .filter(AssistantPlan.executed_at.isnot(None))
                .order_by(AssistantPlan.executed_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {"kind": r.status, "summary": r.summary, "result": r.result}
                for r in rows
            ]
