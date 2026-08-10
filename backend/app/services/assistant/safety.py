"""AI 助手 runtime：安全等级与待确认计划存储。

安全等级（用户可配置项，一期固定两类，未来可迁移到 DB）：
- direct   直接执行（查询类工具）
- confirm  先出计划、用户确认后执行（写操作工具）
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class PendingPlan:
    """一条待确认的执行计划（confirm 级工具被调用时生成）。"""

    plan_id: str
    user_id: int
    session_id: int
    tool: str
    args: dict[str, Any]
    summary: str


class SafetyManager:
    """进程内待确认计划存储（内存态：重启即失效，用户重说一句即可）。"""

    def __init__(self) -> None:
        self._plans: dict[str, PendingPlan] = {}

    def add(self, plan: PendingPlan) -> None:
        self._plans[plan.plan_id] = plan

    def pop(self, plan_id: str, user_id: int) -> PendingPlan | None:
        """取出并删除计划；不属于该用户的计划不删除（防他人确认消耗）。"""
        plan = self._plans.get(plan_id)
        if plan is None or plan.user_id != user_id:
            return None
        del self._plans[plan_id]
        return plan

    def latest(self, user_id: int, session_id: int) -> PendingPlan | None:
        """该用户该会话最近一条未处理的待确认计划（chat 结束后查询用）。"""
        for plan in reversed(list(self._plans.values())):
            if plan.user_id == user_id and plan.session_id == session_id:
                return plan
        return None

    def ids_for(self, user_id: int, session_id: int) -> set[str]:
        """该用户该会话当前全部待处理计划 id（chat 开始前快照，用于区分本轮新增）。"""
        return {
            p.plan_id
            for p in self._plans.values()
            if p.user_id == user_id and p.session_id == session_id
        }

    def latest_not_in(self, user_id: int, session_id: int, exclude: set[str]) -> PendingPlan | None:
        """最近一条不在 exclude 中的待处理计划（仅本轮新产生的）。"""
        for plan in reversed(list(self._plans.values())):
            if plan.user_id == user_id and plan.session_id == session_id and plan.plan_id not in exclude:
                return plan
        return None

    def clear_for_session(self, user_id: int, session_id: int) -> None:
        """删除该用户该会话的全部待确认计划（用于会话删除时清理内存）。"""
        to_remove = [
            pid
            for pid, plan in list(self._plans.items())
            if plan.user_id == user_id and plan.session_id == session_id
        ]
        for pid in to_remove:
            del self._plans[pid]
