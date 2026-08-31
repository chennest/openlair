"""客户端侧补齐后端没有的东西：当前账本、分类名 → id、类型/象限别名。

后端事实（决定了这里为什么不能偷懒）：
- ledger 系列接口缺 `bookId` 直接 400「缺少账本」，没有隐式默认账本。
- `POST /api/ledger` 的 `category`（名字）字段服务端根本不读，省略 `categoryId` 会静默落到
  「其他」，所以分类必须由 CLI 解析成 id 后再发。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from laircli.client import ApiClient
from laircli.errors import CliError

INCOME = "收入"
EXPENSE = "支出"
QUADRANTS = ["重要紧急", "重要不紧急", "紧急不重要", "不重要不紧急"]

_TYPE_ALIASES = {
    "expense": EXPENSE,
    "exp": EXPENSE,
    "out": EXPENSE,
    "-": EXPENSE,
    "支出": EXPENSE,
    "花": EXPENSE,
    "income": INCOME,
    "inc": INCOME,
    "in": INCOME,
    "+": INCOME,
    "收入": INCOME,
}


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    type: str


@dataclass(frozen=True)
class Book:
    id: int
    name: str
    type: str


def map_type(raw: str) -> str:
    """`-t expense|收入|-` → 后端要求的中文枚举；不接受的值直接报错（后端会把一切非「收入」悄悄归成「支出」）。"""
    value = raw.strip()
    hit = _TYPE_ALIASES.get(value.lower()) or _TYPE_ALIASES.get(value)
    if hit is None:
        raise CliError(f"类型不合法：{raw}（可选 expense / income，或 支出 / 收入）")
    return hit


def map_quadrant(raw: str) -> str:
    value = raw.strip()
    if value.isdigit() and 1 <= int(value) <= 4:
        return QUADRANTS[int(value) - 1]
    exact = [q for q in QUADRANTS if q == value]
    if exact:
        return exact[0]
    prefix = [q for q in QUADRANTS if q.startswith(value)]
    if len(prefix) == 1:
        return prefix[0]
    raise CliError(f"象限不合法：{raw}（可选 1-4 或 {'、'.join(QUADRANTS)}）")


def parse_date(raw: str, label: str) -> str:
    value = raw.strip()
    today = date.today()
    if value == "今天":
        return today.isoformat()
    if value == "昨天":
        return (today - timedelta(days=1)).isoformat()
    if value == "明天":
        return (today + timedelta(days=1)).isoformat()
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise CliError(f"{label} 需为 YYYY-MM-DD，当前为 {raw!r}") from None


def resolve_book(client: ApiClient, book_id: int | None, settings_book: int | None) -> tuple[Book, bool]:
    """返回 (账本, 是否显式指定)。未显式指定时取首个 personal 账本，语义对齐总览页。"""
    books = client.get("/api/books") or []
    items = [Book(int(b["id"]), str(b.get("name") or ""), str(b.get("type") or "")) for b in books]
    wanted = book_id if book_id is not None else settings_book
    if wanted is not None:
        for book in items:
            if book.id == wanted:
                return book, True
        raise CliError(f"账本 {wanted} 不存在或你已不在其中：lair book list 看可选")
    if not items:
        raise CliError("还没有账本：先运行 lair book create <名称>")
    primary = next((b for b in items if b.type == "personal"), items[0])
    return primary, False


def resolve_category(client: ApiClient, tx_type: str | None, query: str | None) -> Category | None:
    """分类名/id → Category；解析不到就硬失败，避免静默记成「其他」。

    `tx_type=None` 表示跨收支两侧查找，调用方可用返回的 `type` 反推收支方向。
    """
    if query is None or not query.strip():
        return None
    text = query.strip()
    options = [
        Category(int(c["id"]), str(c.get("name") or ""), str(c.get("type") or ""))
        for c in (client.get("/api/ledger/categories", {"type": tx_type} if tx_type else None) or [])
    ]
    scope = f"「{tx_type}」" if tx_type else ""
    if text.isdigit():
        hit = next((c for c in options if c.id == int(text)), None)
        if hit:
            return hit
        raise CliError(f"分类 id {text} 不在{scope}可选分类里")
    exact = [c for c in options if c.name == text]
    picked = exact or [c for c in options if c.name.startswith(text)]
    if len(picked) == 1:
        return picked[0]
    if len(picked) > 1:
        raise CliError(f"分类「{text}」有歧义：{'、'.join(c.name for c in picked)}")
    names = "、".join(c.name for c in options) or "（无可用分类）"
    raise CliError(f"分类「{text}」不在{scope}可选分类里；可选：{names}")
