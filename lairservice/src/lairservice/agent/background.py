from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock, Thread
from uuid import uuid4


@dataclass
class BackgroundTaskRecord:
    id: str
    name: str
    status: str
    output: str | None = None


class BackgroundTaskManager:
    _slow_keywords = ("install", "build", "test", "deploy", "compile", "sleep")

    def __init__(self) -> None:
        self._tasks: dict[str, BackgroundTaskRecord] = {}
        self._reported: set[str] = set()
        self._lock = Lock()

    def should_run_background(self, tool_name: str, arguments: dict[str, object]) -> bool:
        explicit = arguments.get("run_in_background")
        if isinstance(explicit, bool):
            return explicit
        if tool_name != "bash":
            return False
        command = arguments.get("command")
        if not isinstance(command, str):
            return False
        lowered = command.lower()
        return any(keyword in lowered for keyword in self._slow_keywords)

    def start(self, *, name: str, run: Callable[[], str]) -> str:
        task_id = f"bg_{uuid4().hex[:8]}"
        with self._lock:
            self._tasks[task_id] = BackgroundTaskRecord(id=task_id, name=name, status="running")

        def worker() -> None:
            try:
                output = run()
            except Exception as error:
                output = f"Error: {error}"
            with self._lock:
                self._tasks[task_id] = BackgroundTaskRecord(id=task_id, name=name, status="completed", output=output)

        Thread(target=worker, daemon=True).start()
        return task_id

    def collect_notifications(self) -> list[str]:
        notifications: list[str] = []
        with self._lock:
            for task_id, record in self._tasks.items():
                if record.status != "completed" or task_id in self._reported:
                    continue
                self._reported.add(task_id)
                output = record.output or "(no output)"
                notifications.append(
                    f"<task_notification id=\"{task_id}\" name=\"{record.name}\" status=\"completed\">\n{output}\n</task_notification>"
                )
        return notifications

    def list_tasks(self) -> str:
        with self._lock:
            if not self._tasks:
                return "(no background tasks)"
            lines = [f"{record.id}: {record.name} [{record.status}]" for record in self._tasks.values()]
        return "\n".join(lines)
