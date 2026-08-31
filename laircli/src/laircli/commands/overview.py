"""`lair overview`：总览看板（本月支出 / 待办 / 即将开始 / 习惯）。"""

from __future__ import annotations

from typing import Callable

from laircli import render, state


def show() -> None:
    """本月支出、待办、即将开始的日程与打卡情况一屏看全。"""
    data = state.client().get("/api/overview") or {}
    if state.is_json():
        render.as_json(data)
        return
    month = data.get("monthExpense") or {}
    amount = float(month.get("amount") or 0)
    budget = float(month.get("budget") or 0)
    trend = float(month.get("trend") or 0)
    arrow = "↑" if trend > 0 else ("↓" if trend < 0 else "→")
    used = f"（预算 {budget:,.0f}，已用 {amount / budget * 100:.0f}%）" if budget else ""
    render.log(f"[bold]本月支出[/bold] {amount:,.2f} {arrow}{abs(trend):.1f}% {used}\n")

    _section("待办", data.get("todos"), lambda x: f"{x.get('text')}  [dim]{x.get('time')} · {x.get('tag')}[/dim]")
    _section("即将开始", data.get("upcoming"), lambda x: f"{x.get('text')}  [dim]{x.get('date')}[/dim]")
    _section("习惯", data.get("habits"), lambda x: f"{'✓' if x.get('done') else '·'} {x.get('name')}")


def _section(title: str, items: object, line: Callable[[dict], str]) -> None:
    rows = list(items or [])
    render.log(f"[bold]{title}[/bold]")
    if not rows:
        render.log("  [dim]（无）[/dim]\n")
        return
    for item in rows:
        render.log(f"  {line(item)}")
    render.log("")
