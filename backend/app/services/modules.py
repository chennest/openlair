"""待办 / 日程 / 笔记 / 习惯 的 CRUD 服务 + 总揽聚合。"""

from datetime import date, timedelta

from app.core.envelope import ApiError
from app.repositories.events import EventRepository
from app.repositories.habits import HabitRepository
from app.repositories.ledger import LedgerRepository
from app.repositories.notes import NoteRepository
from app.repositories.todo import TodoRepository
from app.services import iso_z

QUADRANTS = ["重要紧急", "重要不紧急", "紧急不重要", "不重要不紧急"]


class TodoService:
    def __init__(self, repo: TodoRepository) -> None:
        self._repo = repo

    def list(self, user_id: int) -> dict:
        return {"todos": self._dto_list(user_id)}

    def _dto_list(self, user_id: int) -> list[dict]:
        return [
            {
                "id": t.id,
                "text": t.text,
                "quadrant": t.quadrant,
                "done": t.done,
                "due": t.due,
                "createdAt": iso_z(t.created_at),
                "updatedAt": iso_z(t.updated_at),
            }
            for t in self._repo.list_by_user(user_id)
        ]

    def create(self, *, user_id: int, text: str, quadrant: str, due: str) -> dict:
        q = quadrant if quadrant in QUADRANTS else QUADRANTS[1]
        item = self._repo.create(user_id=user_id, text=text or "", quadrant=q, due=due or "今天")
        return {"id": item.id, "item": next((t for t in self._dto_list(user_id) if t["id"] == item.id), None)}

    def update(self, *, user_id: int, todo_id: int, patch: dict) -> dict:
        if self._repo.get(todo_id) is None:
            raise ApiError(404, "待办不存在")
        clean = {k: v for k, v in patch.items() if k in {"text", "quadrant", "done", "due"} and v is not None}
        self._repo.update(todo_id, clean)
        return {"item": next((t for t in self._dto_list(user_id) if t["id"] == todo_id), None)}

    def remove(self, *, todo_id: int) -> None:
        if not self._repo.delete(todo_id):
            raise ApiError(404, "待办不存在")


class EventService:
    def __init__(self, repo: EventRepository) -> None:
        self._repo = repo

    def list(self, user_id: int) -> dict:
        return {"events": self._dto_list(user_id)}

    def _dto_list(self, user_id: int) -> list[dict]:
        return [
            {
                "id": e.id,
                "title": e.title,
                "date": e.date.isoformat(),
                "time": e.time,
                "location": e.location,
                "done": e.done,
                "createdAt": iso_z(e.created_at),
                "updatedAt": iso_z(e.updated_at),
            }
            for e in self._repo.list_by_user(user_id)
        ]

    def create(
        self, *, user_id: int, title: str, event_date: date, time: str, location: str
    ) -> dict:
        item = self._repo.create(
            user_id=user_id, title=title or "", date=event_date or date.today(), time=time or "10:00", location=location or ""
        )
        return {"id": item.id, "item": next((e for e in self._dto_list(user_id) if e["id"] == item.id), None)}

    def update(self, *, user_id: int, event_id: int, patch: dict) -> dict:
        if self._repo.get(event_id) is None:
            raise ApiError(404, "日程不存在")
        clean = {k: v for k, v in patch.items() if k in {"title", "date", "time", "location", "done"} and v is not None}
        if "date" in clean:
            clean["date"] = date.fromisoformat(str(clean["date"]))
        self._repo.update(event_id, clean)
        return {"item": next((e for e in self._dto_list(user_id) if e["id"] == event_id), None)}

    def remove(self, *, event_id: int) -> None:
        if not self._repo.delete(event_id):
            raise ApiError(404, "日程不存在")


class NoteService:
    def __init__(self, repo: NoteRepository) -> None:
        self._repo = repo

    def list(self, user_id: int) -> dict:
        return {"notes": self._dto_list(user_id)}

    def _dto_list(self, user_id: int) -> list[dict]:
        return [
            {
                "id": n.id,
                "title": n.title,
                "summary": n.summary,
                "tags": n.tags or [],
                "updatedAt": iso_z(n.updated_at),
                "createdAt": iso_z(n.created_at),
            }
            for n in self._repo.list_by_user(user_id)
        ]

    def create(self, *, user_id: int, title: str, summary: str, tags: list[str]) -> dict:
        item = self._repo.create(user_id=user_id, title=title or "未命名", summary=summary or "", tags=tags or [])
        return {"id": item.id, "item": next((n for n in self._dto_list(user_id) if n["id"] == item.id), None)}

    def update(self, *, user_id: int, note_id: int, patch: dict) -> dict:
        if self._repo.get(note_id) is None:
            raise ApiError(404, "笔记不存在")
        clean = {k: v for k, v in patch.items() if k in {"title", "summary", "tags"} and v is not None}
        self._repo.update(note_id, clean)
        return {"item": next((n for n in self._dto_list(user_id) if n["id"] == note_id), None)}

    def remove(self, *, note_id: int) -> None:
        if not self._repo.delete(note_id):
            raise ApiError(404, "笔记不存在")


class HabitService:
    def __init__(self, repo: HabitRepository) -> None:
        self._repo = repo

    def list(self, user_id: int) -> dict:
        return {"habits": self._dto_list(user_id)}

    def _dto_list(self, user_id: int) -> list[dict]:
        return [
            {
                "id": h.id,
                "name": h.name,
                "streak": h.streak,
                "done": h.done,
                "week": h.week or [False] * 7,
                "createdAt": iso_z(h.created_at),
                "updatedAt": iso_z(h.updated_at),
            }
            for h in self._repo.list_by_user(user_id)
        ]

    def create(self, *, user_id: int, name: str) -> dict:
        item = self._repo.create(user_id=user_id, name=name or "新习惯")
        return {"id": item.id, "item": next((h for h in self._dto_list(user_id) if h["id"] == item.id), None)}

    def update(self, *, user_id: int, habit_id: int, patch: dict) -> dict:
        if self._repo.get(habit_id) is None:
            raise ApiError(404, "习惯不存在")
        clean = {k: v for k, v in patch.items() if k in {"name", "streak", "done", "week"} and v is not None}
        self._repo.update(habit_id, clean)
        return {"item": next((h for h in self._dto_list(user_id) if h["id"] == habit_id), None)}

    def remove(self, *, habit_id: int) -> None:
        if not self._repo.delete(habit_id):
            raise ApiError(404, "习惯不存在")


class OverviewService:
    """总揽页：从各模块聚合真实数据。"""

    def __init__(
        self,
        *,
        ledger: LedgerRepository,
        todo: TodoRepository,
        events: EventRepository,
        habits: HabitRepository,
    ) -> None:
        self._ledger = ledger
        self._todo = todo
        self._events = events
        self._habits = habits

    def get(self, *, user_id: int) -> dict:
        today = date.today()
        month_key = f"{today.year}-{today.month:02d}"

        rows = self._ledger.query_transactions(book_id=1)
        month_expense = sum(
            (float(r.amount) for r in rows if r.type == "支出" and r.date.strftime("%Y-%m") == month_key), 0.0
        )
        prev = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        prev_expense = sum(
            (float(r.amount) for r in rows if r.type == "支出" and r.date.strftime("%Y-%m") == prev), 0.0
        )
        trend = round((month_expense - prev_expense) / prev_expense * 100, 1) if prev_expense else 0.0
        budget = self._ledger.budget_for(1, month_key)

        return {
            "monthExpense": {
                "amount": round(month_expense, 2),
                "budget": round(float(budget.expense_limit), 2),
                "trend": trend,
            },
            "todos": [
                {"text": t.text, "time": t.due, "tag": t.quadrant, "tagClass": "red" if t.quadrant == "重要紧急" else "gray"}
                for t in self._todo.list_by_user(user_id)
                if not t.done
            ][:4],
            "upcoming": [
                {
                    "text": e.title,
                    "date": f"{e.date.isoformat()} {e.time}",
                    "tag": "日程",
                    "tagClass": "green",
                }
                for e in sorted(
                    (e for e in self._events.list_by_user(user_id) if e.date >= today),
                    key=lambda e: (e.date, e.id),
                )
            ][:3],
            "habits": [{"name": h.name, "done": h.done} for h in self._habits.list_by_user(user_id)][:4],
        }
