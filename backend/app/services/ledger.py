"""记账服务：分类 / 流水列表（筛选+分页+摘要+统计）/ 趋势 / 预算 / 增删改。"""

from datetime import date, datetime, timedelta

from app.core.envelope import ApiError
from app.models.transaction import Transaction
from app.repositories.ledger import LedgerRepository
from app.repositories.users import UserRepository

DEFAULT_BOOK_ID = 1  # 个人账本


def _money(value) -> float:
    return round(float(value), 2)


def _tx_dto(tx: Transaction, category_name: str, user_name: str) -> dict:
    return {
        "id": tx.id,
        "type": tx.type,
        "categoryId": tx.category_id,
        "category": category_name,
        "bookId": tx.book_id,
        "userId": tx.user_id,
        "userName": user_name,
        "amount": _money(tx.amount),
        "date": tx.date.isoformat(),
        "note": tx.note,
    }


def summarize(rows: list[Transaction]) -> dict:
    income = sum((float(r.amount) for r in rows if r.type == "收入"), 0.0)
    expense = sum((float(r.amount) for r in rows if r.type == "支出"), 0.0)
    return {
        "income": _money(income),
        "expense": _money(expense),
        "balance": _money(income - expense),
    }


def category_stats(rows: list[Transaction], category_names: dict[int, str]) -> list[dict]:
    expenses = [r for r in rows if r.type == "支出"]
    total = sum((float(r.amount) for r in expenses), 0.0) or 1.0
    buckets: dict[int, float] = {}
    for r in expenses:
        buckets[r.category_id] = buckets.get(r.category_id, 0.0) + float(r.amount)
    stats = [
        {
            "categoryId": cid,
            "name": category_names.get(cid, "其他"),
            "amount": _money(amount),
            "percent": round(amount / total * 100, 1),
        }
        for cid, amount in buckets.items()
    ]
    return sorted(stats, key=lambda s: s["amount"], reverse=True)


def monthly_trend(rows: list[Transaction], months: int = 6) -> list[dict]:
    points: list[dict] = []
    today = date.today()
    for offset in range(months - 1, -1, -1):
        first = (today.replace(day=1) - timedelta(days=offset * 31)).replace(day=1)
        key = f"{first.year}-{first.month:02d}"
        income = 0.0
        expense = 0.0
        for r in rows:
            if r.date.year == first.year and r.date.month == first.month:
                if r.type == "收入":
                    income += float(r.amount)
                else:
                    expense += float(r.amount)
        points.append({"month": key, "income": _money(income), "expense": _money(expense)})
    return points


class LedgerService:
    def __init__(self, ledger: LedgerRepository, users: UserRepository) -> None:
        self._ledger = ledger
        self._users = users

    # ---------- 分类 ----------

    def categories(self, type: str | None = None) -> list[dict]:
        return [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "sortOrder": c.sort_order,
                "isDefault": c.is_default,
            }
            for c in self._ledger.categories(type)
        ]

    # ---------- 列表（含摘要/统计/分页/预算） ----------

    def list_transactions(
        self,
        *,
        book_id: int | None = None,
        type: str | None = None,
        category_id: int | None = None,
        keyword: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        bid = book_id or DEFAULT_BOOK_ID
        rows = self._ledger.query_transactions(
            book_id=bid,
            type=type or None,
            category_id=category_id,
            keyword=keyword or None,
            start_date=start_date,
            end_date=end_date,
        )
        total = len(rows)
        start = (max(1, page) - 1) * page_size
        page_rows = rows[start : start + page_size]

        names = {c.id: c.name for c in self._ledger.categories()}
        users = {
            u.id: u.name
            for u in (self._users.by_id(uid) for uid in {r.user_id for r in rows})
            if u is not None
        }
        budget = self._ledger.budget_for(bid, f"{date.today().year}-{date.today().month:02d}")

        return {
            "summary": summarize(rows),
            "categoryStats": category_stats(rows, names),
            "transactions": [
                _tx_dto(r, names.get(r.category_id, "其他"), users.get(r.user_id, "未知")) for r in page_rows
            ],
            "total": total,
            "page": max(1, page),
            "pageSize": page_size,
            "budget": _money(budget.expense_limit),
        }

    def trend(self, *, book_id: int | None = None, months: int = 6) -> list[dict]:
        bid = book_id or DEFAULT_BOOK_ID
        rows = self._ledger.query_transactions(book_id=bid)
        return monthly_trend(rows, months)

    def get_budget(self, *, book_id: int | None = None) -> dict:
        bid = book_id or DEFAULT_BOOK_ID
        budget = self._ledger.budget_for(bid, f"{date.today().year}-{date.today().month:02d}")
        return {"budget": _money(budget.expense_limit)}

    def update_budget(self, *, book_id: int | None, amount: float) -> dict:
        if amount is None or amount < 0:
            raise ApiError(400, "预算金额不合法")
        bid = book_id or DEFAULT_BOOK_ID
        budget = self._ledger.update_budget(bid, f"{date.today().year}-{date.today().month:02d}", amount)
        return {"budget": _money(budget.expense_limit)}

    # ---------- 流水增删改 ----------

    def create(
        self,
        *,
        user_id: int,
        type: str,
        category_id: int | None,
        amount: float,
        date: date | None,
        note: str,
        book_id: int | None,
    ) -> dict:
        tx_type = "收入" if type == "收入" else "支出"
        cid = category_id
        if not cid:
            # 兼容：传分类名 → 查表；否则兜底「其他」
            default = self._ledger.default_category(tx_type)
            cid = default.id if default else None
        if not cid:
            raise ApiError(400, "分类不存在")
        tx = self._ledger.create_transaction(
            type=tx_type,
            category_id=cid,
            book_id=book_id or DEFAULT_BOOK_ID,
            user_id=user_id,
            amount=amount or 0,
            date=date or datetime.now().date(),
            note=note or "",
        )
        names = {c.id: c.name for c in self._ledger.categories()}
        user = self._users.by_id(user_id)
        return {"id": tx.id, "item": _tx_dto(tx, names.get(tx.category_id, "其他"), user.name if user else "未知")}

    def update(self, *, user_id: int, transaction_id: int, patch: dict) -> dict:
        tx = self._ledger.get_transaction(transaction_id)
        if tx is None:
            raise ApiError(404, "流水不存在")
        allowed = {"type", "categoryId", "amount", "date", "note", "bookId"}
        clean: dict = {}
        for key, value in patch.items():
            if key not in allowed or value is None:
                continue
            if key == "type":
                clean["type"] = "收入" if value == "收入" else "支出"
            elif key == "categoryId":
                clean["category_id"] = int(value)
            elif key == "date":
                clean["date"] = date.fromisoformat(str(value))
            elif key == "bookId":
                clean["book_id"] = int(value)
            else:
                clean[key] = value
        updated = self._ledger.update_transaction(transaction_id, clean)
        names = {c.id: c.name for c in self._ledger.categories()}
        user = self._users.by_id(user_id)
        return {"item": _tx_dto(updated, names.get(updated.category_id, "其他"), user.name if user else "未知")}

    def remove(self, *, transaction_id: int) -> None:
        if not self._ledger.delete_transaction(transaction_id):
            raise ApiError(404, "流水不存在")
