"""`lair ledger`：流水增删改查 / 分类 / 趋势 / 预算。"""

from __future__ import annotations

from typing import Optional

import typer

from laircli import render, resolver, state

app = typer.Typer(help="记账：流水 / 分类 / 趋势 / 预算", no_args_is_help=True)


def _book(book_id: Optional[int]):
    return resolver.resolve_book(state.client(), book_id, state.settings().book_id)


def _money(value: object) -> str:
    try:
        return f"{float(str(value)):,.2f}"
    except (TypeError, ValueError):
        return str(value)


@app.command("add")
def add(
    amount: float = typer.Argument(..., help="金额"),
    type_: Optional[str] = typer.Option(None, "--type", "-t", help="expense/income 或 支出/收入（省略则按分类推断）"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="分类名或 id"),
    date_: Optional[str] = typer.Option(None, "--date", "-d", help="YYYY-MM-DD / 今天 / 昨天"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="备注"),
    book: Optional[int] = typer.Option(None, "--book", "-b", help="账本 id（覆盖默认）"),
) -> None:
    """记一笔账。"""
    client = state.client()
    wanted_type = resolver.map_type(type_) if type_ else None
    picked = resolver.resolve_category(client, wanted_type, category)
    tx_type = wanted_type or (picked.type if picked else resolver.EXPENSE)
    target, explicit = _book(book)
    body = {
        "type": tx_type,
        "amount": amount,
        "bookId": target.id,
        "categoryId": picked.id if picked else None,
        "date": resolver.parse_date(date_, "--date") if date_ else None,
        "note": note,
    }
    data = client.post("/api/ledger", body)
    item = data.get("item") or {}
    if state.is_json():
        render.as_json(data)
        return
    if not explicit:
        render.hint(f"账本：{target.name}（#{target.id}）—— 用 lair book use <id> 设默认")
    render.ok(
        f"#{data.get('id')} 已记 {item.get('type')} {_money(item.get('amount'))}"
        f" · {item.get('category')} · {item.get('date')}"
        + (f" · {item.get('note')}" if item.get("note") else "")
    )
    if picked is None:
        render.hint("未指定分类，服务端按「其他」入账（下次用 -c 餐饮）")


@app.command("list")
def list_(
    type_: Optional[str] = typer.Option(None, "--type", "-t"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="匹配备注或分类名"),
    start: Optional[str] = typer.Option(None, "--start", help="起始日期 YYYY-MM-DD"),
    end: Optional[str] = typer.Option(None, "--end", help="结束日期 YYYY-MM-DD"),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(20, "--page-size", min=1, max=200),
    book: Optional[int] = typer.Option(None, "--book", "-b"),
) -> None:
    """查流水（含区间汇总与预算）。"""
    client = state.client()
    tx_type = resolver.map_type(type_) if type_ else None
    picked = resolver.resolve_category(client, tx_type, category)
    target, explicit = _book(book)
    data = client.get(
        "/api/ledger",
        {
            "bookId": target.id,
            "type": tx_type,
            "categoryId": picked.id if picked else None,
            "keyword": keyword,
            "startDate": resolver.parse_date(start, "--start") if start else None,
            "endDate": resolver.parse_date(end, "--end") if end else None,
            "page": page,
            "pageSize": page_size,
        },
    )
    if state.is_json():
        render.as_json(data)
        return
    if not explicit:
        render.hint(f"账本：{target.name}（#{target.id}）—— 用 lair book use <id> 设默认")
    rows = [
        [
            t.get("id"),
            t.get("date"),
            t.get("type"),
            t.get("category"),
            _money(t.get("amount")),
            t.get("note"),
            t.get("userName"),
        ]
        for t in data.get("transactions") or []
    ]
    render.table(
        [("ID", "right"), ("日期", "left"), ("类型", "left"), ("分类", "left"),
         ("金额", "right"), ("备注", "left"), ("记账人", "left")],
        rows,
    )
    summary = data.get("summary") or {}
    render.log(
        f"收入 {_money(summary.get('income'))} ｜ 支出 {_money(summary.get('expense'))}"
        f" ｜ 结余 {_money(summary.get('balance'))} ｜ 当月预算 {_money(data.get('budget'))}"
        f" ｜ 共 {data.get('total')} 条（第 {data.get('page')} 页，每页 {data.get('pageSize')}）"
    )


@app.command("edit")
def edit(
    transaction_id: int = typer.Argument(...),
    amount: Optional[float] = typer.Option(None, "--amount"),
    type_: Optional[str] = typer.Option(None, "--type", "-t"),
    category: Optional[str] = typer.Option(None, "--category", "-c"),
    date_: Optional[str] = typer.Option(None, "--date", "-d"),
    note: Optional[str] = typer.Option(None, "--note", "-n"),
) -> None:
    """改一笔流水（只提交显式给的字段；后端不支持清空）。"""
    client = state.client()
    body: dict = {}
    if amount is not None:
        body["amount"] = amount
    if type_:
        body["type"] = resolver.map_type(type_)
    if date_:
        body["date"] = resolver.parse_date(date_, "--date")
    if note is not None:
        body["note"] = note
    if category:
        if not type_:
            raise typer.BadParameter("改分类需同时给 --type，避免分类与收支方向不一致")
        picked = resolver.resolve_category(client, resolver.map_type(type_), category)
        if picked:
            body["categoryId"] = picked.id
    if not body:
        raise typer.BadParameter("至少要给一个修改项（--amount/--type/--category/--date/--note）")
    data = client.put(f"/api/ledger/{transaction_id}", body)
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"#{transaction_id} 已更新 → {item.get('type')} {_money(item.get('amount'))} · {item.get('category')}")


@app.command("rm")
def remove(transaction_id: int = typer.Argument(...)) -> None:
    """删一笔流水。"""
    state.client().delete(f"/api/ledger/{transaction_id}")
    render.ok(f"#{transaction_id} 已删除")


@app.command("categories")
def categories(
    type_: Optional[str] = typer.Option(None, "--type", "-t"),
) -> None:
    """列出可用分类（全局固定 1-16）。"""
    tx_type = resolver.map_type(type_) if type_ else None
    data = state.client().get("/api/ledger/categories", {"type": tx_type}) or []
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("名称", "left"), ("类型", "left"), ("默认", "left")],
        [[c.get("id"), c.get("name"), c.get("type"), "是" if c.get("isDefault") else ""] for c in data],
    )


@app.command("trend")
def trend(book: Optional[int] = typer.Option(None, "--book", "-b")) -> None:
    """近 6 个月收支趋势。"""
    target, explicit = _book(book)
    data = state.client().get("/api/ledger/trend", {"bookId": target.id}) or []
    if state.is_json():
        render.as_json(data)
        return
    if not explicit:
        render.hint(f"账本：{target.name}（#{target.id}）")
    render.table(
        [("月份", "left"), ("收入", "right"), ("支出", "right"), ("", "left")],
        [[m.get("month"), _money(m.get("income")), _money(m.get("expense")), _bars(m.get("expense"))] for m in data],
    )


@app.command("budget")
def budget(
    amount: Optional[float] = typer.Argument(None, help="留空=查询；给值=设置当月预算"),
    book: Optional[int] = typer.Option(None, "--book", "-b"),
) -> None:
    """查/改当月预算。"""
    client = state.client()
    target, explicit = _book(book)
    if amount is None:
        data = client.get("/api/ledger/budget", {"bookId": target.id})
        if state.is_json():
            render.as_json(data)
            return
        if not explicit:
            render.hint(f"账本：{target.name}（#{target.id}）")
        render.log(f"{target.name} 当月预算：{_money((data or {}).get('budget'))}")
        return
    data = client.put("/api/ledger/budget", {"bookId": target.id, "amount": amount})
    if state.is_json():
        render.as_json(data)
        return
    render.ok(f"{target.name} 当月预算已设为 {_money((data or {}).get('budget'))}")


def _bars(expense: object) -> str:
    try:
        value = float(str(expense))
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    return "█" * max(1, min(30, int(value / 200)))
