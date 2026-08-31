"""`lair cal`：日程列表 / 新增 / 完成 / 删除（服务端不分页，按日期区间客户端筛选）。"""

from __future__ import annotations

from typing import Optional

import typer

from laircli import render, resolver, state

app = typer.Typer(help="日程", no_args_is_help=True)


def _events() -> list[dict]:
    data = (state.client().get("/api/calendar") or {}).get("events") or []
    return sorted(data, key=lambda e: (str(e.get("date") or ""), str(e.get("time") or "")))


@app.command("list")
def list_(
    day: Optional[str] = typer.Option(None, "--day", help="只看某天 YYYY-MM-DD / 今天"),
    start: Optional[str] = typer.Option(None, "--from", help="起始日期"),
    end: Optional[str] = typer.Option(None, "--to", help="结束日期"),
    open_only: bool = typer.Option(False, "--open", "-o", help="只看未完成"),
) -> None:
    """日程清单。"""
    data = _events()
    if day:
        target = resolver.parse_date(day, "--day")
        data = [e for e in data if e.get("date") == target]
    else:
        if start:
            low = resolver.parse_date(start, "--from")
            data = [e for e in data if str(e.get("date") or "") >= low]
        if end:
            high = resolver.parse_date(end, "--to")
            data = [e for e in data if str(e.get("date") or "") <= high]
    if open_only:
        data = [e for e in data if not e.get("done")]
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("日期", "left"), ("时间", "left"), ("标题", "left"), ("地点", "left"), ("状态", "center")],
        [
            [e.get("id"), e.get("date"), e.get("time"), e.get("title"), e.get("location"), "✓" if e.get("done") else "·"]
            for e in data
        ],
    )


@app.command("add")
def add(
    title: str = typer.Argument(..., help="日程标题（1-200 字）"),
    date_: Optional[str] = typer.Option(None, "--date", "-d", help="YYYY-MM-DD / 今天 / 明天"),
    time: Optional[str] = typer.Option(None, "--time", "-T", help="如 09:30，默认 10:00"),
    location: Optional[str] = typer.Option(None, "--location", "-l"),
) -> None:
    """新增日程。"""
    body: dict = {"title": title}
    if date_:
        body["date"] = resolver.parse_date(date_, "--date")
    if time:
        body["time"] = time
    if location:
        body["location"] = location
    data = state.client().post("/api/calendar", body)
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"#{data.get('id')} 已安排：{item.get('date')} {item.get('time')} {item.get('title')}")


@app.command("done")
def done(event_id: int = typer.Argument(...)) -> None:
    """标记完成。"""
    state.client().put(f"/api/calendar/{event_id}", {"done": True})
    render.ok(f"#{event_id} 已完成")


@app.command("undo")
def undo(event_id: int = typer.Argument(...)) -> None:
    """标记未完成。"""
    state.client().put(f"/api/calendar/{event_id}", {"done": False})
    render.ok(f"#{event_id} 已恢复为未完成")


@app.command("rm")
def remove(event_id: int = typer.Argument(...)) -> None:
    """删除日程。"""
    state.client().delete(f"/api/calendar/{event_id}")
    render.ok(f"#{event_id} 已删除")
