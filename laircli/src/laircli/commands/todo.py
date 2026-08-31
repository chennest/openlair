"""`lair todo`：待办列表 / 新增 / 完成 / 删除。"""

from __future__ import annotations

from typing import Optional

import typer

from laircli import render, resolver, state

app = typer.Typer(help="待办", no_args_is_help=True)


def _todos() -> list[dict]:
    return (state.client().get("/api/todo") or {}).get("todos") or []


@app.command("list")
def list_(open_only: bool = typer.Option(False, "--open", "-o", help="只看未完成")) -> None:
    """待办清单。"""
    data = _todos()
    if open_only:
        data = [t for t in data if not t.get("done")]
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("状态", "center"), ("内容", "left"), ("象限", "left"), ("期限", "left")],
        [
            [
                t.get("id"),
                "✓" if t.get("done") else "·",
                t.get("text"),
                t.get("quadrant"),
                t.get("due"),
            ]
            for t in data
        ],
    )


@app.command("add")
def add(
    text: str = typer.Argument(..., help="待办内容（1-200 字）"),
    quadrant: Optional[str] = typer.Option(None, "--quadrant", "-q", help="1-4 或 重要紧急 等"),
    due: Optional[str] = typer.Option(None, "--due", "-d", help="期限自由文本，如 今天/明天/本周"),
) -> None:
    """新增待办。"""
    body: dict = {"text": text}
    if quadrant:
        body["quadrant"] = resolver.map_quadrant(quadrant)
    if due:
        body["due"] = due
    data = state.client().post("/api/todo", body)
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"#{data.get('id')} 已添加：{item.get('text')}（{item.get('quadrant')} · {item.get('due')}）")


@app.command("done")
def done(todo_id: int = typer.Argument(...)) -> None:
    """标记完成。"""
    state.client().put(f"/api/todo/{todo_id}", {"done": True})
    render.ok(f"#{todo_id} 已完成")


@app.command("undo")
def undo(todo_id: int = typer.Argument(...)) -> None:
    """标记未完成。"""
    state.client().put(f"/api/todo/{todo_id}", {"done": False})
    render.ok(f"#{todo_id} 已恢复为未完成")


@app.command("edit")
def edit(
    todo_id: int = typer.Argument(...),
    text: Optional[str] = typer.Option(None, "--text"),
    quadrant: Optional[str] = typer.Option(None, "--quadrant", "-q"),
    due: Optional[str] = typer.Option(None, "--due", "-d"),
) -> None:
    """修改待办。"""
    body: dict = {}
    if text:
        body["text"] = text
    if quadrant:
        body["quadrant"] = resolver.map_quadrant(quadrant)
    if due:
        body["due"] = due
    if not body:
        raise typer.BadParameter("至少要给一个修改项（--text/--quadrant/--due）")
    state.client().put(f"/api/todo/{todo_id}", body)
    render.ok(f"#{todo_id} 已更新")


@app.command("rm")
def remove(todo_id: int = typer.Argument(...)) -> None:
    """删除待办。"""
    state.client().delete(f"/api/todo/{todo_id}")
    render.ok(f"#{todo_id} 已删除")
