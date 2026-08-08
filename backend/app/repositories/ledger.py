from datetime import date

from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction


class LedgerRepository:
    """记账仓储：分类 / 流水 / 预算。"""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    # ---------- 分类 ----------

    def categories(self, type: str | None = None) -> list[Category]:
        with self._session_factory() as session:
            stmt = select(Category).order_by(Category.sort_order, Category.id)
            if type:
                stmt = stmt.where(Category.type == type)
            return list(session.scalars(stmt))

    def category_by_name(self, name: str) -> Category | None:
        with self._session_factory() as session:
            return session.scalar(select(Category).where(Category.name == name))

    def default_category(self, type: str) -> Category | None:
        with self._session_factory() as session:
            return session.scalar(
                select(Category).where(Category.type == type, Category.is_default.is_(True)).order_by(Category.id)
            )

    # ---------- 流水 ----------

    def query_transactions(
        self,
        *,
        book_id: int,
        type: str | None = None,
        category_id: int | None = None,
        keyword: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """按条件筛选 + 日期倒序（SQL 层完成过滤，语义与 mock Repository 对齐）。"""
        stmt = select(Transaction).where(Transaction.book_id == book_id)
        if type:
            stmt = stmt.where(Transaction.type == type)
        if category_id:
            stmt = stmt.where(Transaction.category_id == category_id)
        if start_date:
            stmt = stmt.where(Transaction.date >= start_date)
        if end_date:
            stmt = stmt.where(Transaction.date <= end_date)
        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
        with self._session_factory() as session:
            rows = list(session.scalars(stmt))
        if keyword:
            kw = keyword.lower()
            names = {c.id: c.name for c in self.categories()}
            rows = [t for t in rows if kw in t.note.lower() or kw in names.get(t.category_id, "").lower()]
        return rows

    def get_transaction(self, transaction_id: int) -> Transaction | None:
        with self._session_factory() as session:
            return session.get(Transaction, transaction_id)

    def create_transaction(
        self,
        *,
        type: str,
        category_id: int,
        book_id: int,
        user_id: int,
        amount: float,
        date: date,
        note: str,
    ) -> Transaction:
        with self._session_factory() as session:
            tx = Transaction(
                type=type,
                category_id=category_id,
                book_id=book_id,
                user_id=user_id,
                amount=amount,
                date=date,
                note=note,
            )
            session.add(tx)
            session.commit()
            session.refresh(tx)
            return tx

    def update_transaction(self, transaction_id: int, patch: dict) -> Transaction | None:
        with self._session_factory() as session:
            tx = session.get(Transaction, transaction_id)
            if tx is None:
                return None
            for key, value in patch.items():
                if hasattr(tx, key):
                    setattr(tx, key, value)
            session.commit()
            session.refresh(tx)
            return tx

    def delete_transaction(self, transaction_id: int) -> bool:
        with self._session_factory() as session:
            tx = session.get(Transaction, transaction_id)
            if tx is None:
                return False
            session.delete(tx)
            session.commit()
            return True

    # ---------- 预算 ----------

    def budget_for(self, book_id: int, month: str) -> Budget:
        """读取当月预算；不存在则创建默认 5000（与 mock currentBudget 语义一致）。"""
        with self._session_factory() as session:
            budget = session.scalar(select(Budget).where(Budget.book_id == book_id, Budget.month == month))
            if budget is not None:
                return budget
            budget = Budget(book_id=book_id, month=month, expense_limit=5000)
            session.add(budget)
            session.commit()
            session.refresh(budget)
            return budget

    def update_budget(self, book_id: int, month: str, amount: float) -> Budget:
        with self._session_factory() as session:
            budget = session.scalar(select(Budget).where(Budget.book_id == book_id, Budget.month == month))
            if budget is None:
                budget = Budget(book_id=book_id, month=month, expense_limit=amount)
                session.add(budget)
            else:
                budget.expense_limit = amount
            session.commit()
            session.refresh(budget)
            return budget
