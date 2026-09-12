"""待办 / 日程 / 笔记 / 习惯 / 倒数日 的 CRUD 服务 + 总览聚合。"""

import calendar
from datetime import date, timedelta

from app.core.envelope import ApiError
from app.repositories.books import BookRepository
from app.repositories.days import DayRepository
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


class DayService:
    """倒数日 / 纪念日：重复规则展开为下一次日期，倒数天数与周年数在 DTO 统一计算。"""

    REPEATS = ("once", "yearly", "monthly")

    def __init__(self, repo: DayRepository) -> None:
        self._repo = repo

    def list(self, user_id: int) -> dict:
        today = date.today()
        dtos = [self._dto(item, today) for item in self._repo.list_by_user(user_id)]
        # 置顶在前，其余按「距离天数」绝对值升序（今天/临近在前，久远的累计日在后）
        dtos.sort(key=lambda d: (not d["pinned"], abs(d["daysUntil"]), d["id"]))
        return {"days": dtos}

    def create(
        self, *, user_id: int, title: str, day_date: date, emoji: str, repeat: str, pinned: bool
    ) -> dict:
        item = self._repo.create(
            user_id=user_id,
            title=(title or "").strip() or "未命名日子",
            date=day_date,
            emoji=(emoji or "")[:8],
            repeat=repeat if repeat in self.REPEATS else "once",
            pinned=bool(pinned),
        )
        return {"id": item.id, "item": self._dto(item, date.today())}

    def update(self, *, user_id: int, day_id: int, patch: dict) -> dict:
        if self._repo.get(day_id) is None:
            raise ApiError(404, "日子不存在")
        clean = {
            k: v for k, v in patch.items()
            if k in {"title", "emoji", "date", "repeat", "pinned"} and v is not None
        }
        if "title" in clean:
            clean["title"] = str(clean["title"]).strip() or "未命名日子"
        if "emoji" in clean:
            clean["emoji"] = str(clean["emoji"])[:8]
        if "repeat" in clean and clean["repeat"] not in self.REPEATS:
            clean["repeat"] = "once"
        if "date" in clean:
            clean["date"] = date.fromisoformat(str(clean["date"]))
        item = self._repo.update(day_id, clean)
        return {"item": self._dto(item, date.today())}

    def remove(self, *, day_id: int) -> None:
        if not self._repo.delete(day_id):
            raise ApiError(404, "日子不存在")

    @staticmethod
    def _next_due(d: date, repeat: str, today: date) -> date:
        """展开下一次日期：once=原日期；yearly=今年周年（已过取明年，2/29 平年落 2/28）；
        monthly=本月同日（已过取下月，月末截断到当月最后一天）。"""
        if repeat == "yearly":
            try:
                candidate = d.replace(year=today.year)
            except ValueError:  # 2/29 出生平年
                candidate = date(today.year, 2, 28)
            if candidate < today:
                try:
                    candidate = d.replace(year=today.year + 1)
                except ValueError:
                    candidate = date(today.year + 1, 2, 28)
            return candidate
        if repeat == "monthly":

            def month_day(year: int, month: int) -> date:
                last = calendar.monthrange(year, month)[1]
                return date(year, month, min(d.day, last))

            candidate = month_day(today.year, today.month)
            if candidate < today:
                y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
                candidate = month_day(y, m)
            return candidate
        return d

    def _dto(self, item, today: date) -> dict:
        due = self._next_due(item.date, item.repeat, today)
        days_until = (due - today).days
        # 每年重复时给出第几次周年/生日（如 3 = 3 岁生日）；一次性无此概念
        milestone = due.year - item.date.year + 1 if item.repeat == "yearly" else None
        return {
            "id": item.id,
            "title": item.title,
            "emoji": item.emoji,
            "date": item.date.isoformat(),
            "repeat": item.repeat,
            "pinned": bool(item.pinned),
            "daysUntil": days_until,
            "milestone": milestone,
            "createdAt": iso_z(item.created_at),
            "updatedAt": iso_z(item.updated_at),
        }


class OverviewService:
    """总览页：从各模块聚合真实数据（按当前用户的主账本隔离）。"""

    def __init__(
        self,
        *,
        ledger: LedgerRepository,
        todo: TodoRepository,
        events: EventRepository,
        habits: HabitRepository,
        books: BookRepository,
    ) -> None:
        self._ledger = ledger
        self._todo = todo
        self._events = events
        self._habits = habits
        self._books = books

    def _primary_book_id(self, user_id: int) -> int | None:
        """当前用户的主账本：优先 personal，否则第一个账本；无账本返回 None。"""
        books = self._books.list_all(user_id)
        if not books:
            return None
        book = next((b for b in books if b.type == "personal"), books[0])
        return book.id

    def get(self, *, user_id: int) -> dict:
        today = date.today()
        month_key = f"{today.year}-{today.month:02d}"

        book_id = self._primary_book_id(user_id)
        if book_id is None:
            month_expense = 0.0
            trend = 0.0
            budget_amount = 0.0
            recent_ledger: list[dict] = []
        else:
            rows = self._ledger.query_transactions(book_id=book_id)
            month_expense = sum(
                (float(r.amount) for r in rows if r.type == "支出" and r.date.strftime("%Y-%m") == month_key), 0.0
            )
            prev = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            prev_expense = sum(
                (float(r.amount) for r in rows if r.type == "支出" and r.date.strftime("%Y-%m") == prev), 0.0
            )
            trend = round((month_expense - prev_expense) / prev_expense * 100, 1) if prev_expense else 0.0
            budget_amount = float(self._ledger.budget_for(book_id, month_key).expense_limit)
            cat_names = {c.id: c.name for c in self._ledger.categories()}
            recent_ledger = [
                {
                    "id": t.id,
                    "amount": round(float(t.amount), 2),
                    "type": t.type,
                    "category": cat_names.get(t.category_id, "其他"),
                    "date": t.date.isoformat(),
                    "note": t.note or "",
                }
                for t in rows[:10]
            ]

        return {
            "monthExpense": {
                "amount": round(month_expense, 2),
                "budget": round(budget_amount, 2),
                "trend": trend,
            },
            "recentLedger": recent_ledger,
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
