from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4
import json


@dataclass(frozen=True)
class HarnessTask:
    id: str
    subject: str
    description: str
    status: str
    owner: str | None
    blockedBy: list[str]


class TaskSystem:
    def __init__(self, workspace_path: Path | str) -> None:
        self._tasks_path = Path(workspace_path).resolve() / ".tasks"

    def create_task(self, subject: str, description: str, blockedBy: list[str] | None = None) -> str:
        task = HarnessTask(
            id=f"task_{uuid4().hex[:12]}",
            subject=subject,
            description=description,
            status="pending",
            owner=None,
            blockedBy=blockedBy or [],
        )
        self._save(task)
        return json.dumps(asdict(task), ensure_ascii=False)

    def list_tasks(self) -> str:
        tasks = [asdict(task) for task in self._load_all()]
        return json.dumps(tasks, ensure_ascii=False)

    def get_task(self, task_id: str) -> str:
        task = self._load(task_id)
        if task is None:
            return f"Error: unknown task {task_id}"
        return json.dumps(asdict(task), ensure_ascii=False)

    def claim_task(self, task_id: str, owner: str) -> str:
        task = self._load(task_id)
        if task is None:
            return f"Error: unknown task {task_id}"
        if task.status != "pending":
            return f"Error: task {task_id} is {task.status}"
        blocked = self._unfinished_blockers(task)
        if blocked:
            return f"Error: task {task_id} is blocked by {', '.join(blocked)}"
        claimed = HarnessTask(
            id=task.id,
            subject=task.subject,
            description=task.description,
            status="in_progress",
            owner=owner,
            blockedBy=task.blockedBy,
        )
        self._save(claimed)
        return json.dumps(asdict(claimed), ensure_ascii=False)

    def complete_task(self, task_id: str) -> str:
        task = self._load(task_id)
        if task is None:
            return f"Error: unknown task {task_id}"
        completed = HarnessTask(
            id=task.id,
            subject=task.subject,
            description=task.description,
            status="completed",
            owner=task.owner,
            blockedBy=task.blockedBy,
        )
        self._save(completed)
        unlocked = [candidate.id for candidate in self._load_all() if task_id in candidate.blockedBy and not self._unfinished_blockers(candidate)]
        return json.dumps({"task": asdict(completed), "unlocked": unlocked}, ensure_ascii=False)

    def _task_path(self, task_id: str) -> Path:
        return self._tasks_path / f"{task_id}.json"

    def _save(self, task: HarnessTask) -> None:
        self._tasks_path.mkdir(parents=True, exist_ok=True)
        self._task_path(task.id).write_text(json.dumps(asdict(task), ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self, task_id: str) -> HarnessTask | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return HarnessTask(
            id=str(data["id"]),
            subject=str(data["subject"]),
            description=str(data["description"]),
            status=str(data["status"]),
            owner=data["owner"] if data.get("owner") is None else str(data["owner"]),
            blockedBy=[str(item) for item in data.get("blockedBy", [])],
        )

    def _load_all(self) -> list[HarnessTask]:
        if not self._tasks_path.exists():
            return []
        tasks = []
        for path in sorted(self._tasks_path.glob("*.json")):
            task = self._load(path.stem)
            if task is not None:
                tasks.append(task)
        return tasks

    def _unfinished_blockers(self, task: HarnessTask) -> list[str]:
        unfinished = []
        for blocker_id in task.blockedBy:
            blocker = self._load(blocker_id)
            if blocker is None or blocker.status != "completed":
                unfinished.append(blocker_id)
        return unfinished
