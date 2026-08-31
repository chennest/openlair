"""`lair habit`：习惯列表 / 新建 / 打卡 / 取消打卡 / 删除。"""

from __future__ import annotations

import typer

from laircli import render, state

app = typer.Typer(help="习惯打卡", no_args_is_help=True)


def _habits() -> list[dict]:
    return (state.client().get("/api/habits") or {}).get("habits") or []


def _week(week: object) -> str:
    flags = list(week or [])
    return "".join("▰" if bool(f) else "▱" for f in flags[:7])


@app.command("list")
def list_() -> None:
    """习惯与本周打卡。"""
    data = _habits()
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("习惯", "left"), ("今日", "center"), ("连续", "right"), ("本周", "left")],
        [
            [
                h.get("id"),
                h.get("name"),
                "✓" if h.get("done") else "·",
                f"{h.get('streak')} 天",
                _week(h.get("week")),
            ]
            for h in data
        ],
    )


@app.command("add")
def add(name: str = typer.Argument(..., help="习惯名（1-60 字）")) -> None:
    """新建习惯。"""
    data = state.client().post("/api/habits", {"name": name})
    if state.is_json():
        render.as_json(data)
        return
    render.ok(f"#{data.get('id')} 已新建习惯：{(data.get('item') or {}).get('name')}")


@app.command("check")
def check(habit_id: int = typer.Argument(...)) -> None:
    """今日打卡。"""
    data = state.client().put(f"/api/habits/{habit_id}", {"done": True})
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"{item.get('name')} 今日已打卡（当前连续 {item.get('streak')} 天）")


@app.command("uncheck")
def uncheck(habit_id: int = typer.Argument(...)) -> None:
    """取消今日打卡。"""
    state.client().put(f"/api/habits/{habit_id}", {"done": False})
    render.ok(f"#{habit_id} 已取消今日打卡")


@app.command("rm")
def remove(habit_id: int = typer.Argument(...)) -> None:
    """删除习惯。"""
    state.client().delete(f"/api/habits/{habit_id}")
    render.ok(f"#{habit_id} 已删除")
