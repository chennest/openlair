"""`lair note`：笔记列表 / 详情 / 快速记录 / 删除。"""

from __future__ import annotations

from typing import List, Optional

import typer

from laircli import render, state
from laircli.errors import CliError

app = typer.Typer(help="笔记", no_args_is_help=True)


def _notes() -> list[dict]:
    return (state.client().get("/api/notes") or {}).get("notes") or []


@app.command("list")
def list_() -> None:
    """最近笔记（按更新时间倒序）。"""
    data = _notes()
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("标题", "left"), ("标签", "left"),("摘要", "left"), ("更新于", "left")],
        [
            [
                n.get("id"),
                n.get("title"),
                " ".join(n.get("tags") or []),
                (str(n.get("summary") or ""))[:40],
                n.get("updatedAt"),
            ]
            for n in data
        ],
    )


@app.command("show")
def show(
    note_id: int = typer.Argument(...),
) -> None:
    """看一篇笔记的完整正文（summary 字段）。"""
    hit = next((n for n in _notes() if int(n.get("id") or -1) == note_id), None)
    if hit is None:
        raise CliError(f"笔记 {note_id} 不存在：lair note list 看可选")
    if state.is_json():
        render.as_json(hit)
        return
    tags = " ".join(hit.get("tags") or [])
    render.log(f"[bold]{hit.get('title')}[/bold]" + (f"  [dim]#{tags}[/dim]" if tags else ""))
    render.log(f"[dim]更新于 {hit.get('updatedAt')}[/dim]\n")
    render.log(hit.get("summary") or "（无内容）")


@app.command("add")
def add(
    text: List[str] = typer.Argument(None, help="正文，可多词；也可用 --body"),
    title: Optional[str] = typer.Option(None, "--title", help="标题，默认「未命名」"),
    body: Optional[str] = typer.Option(None, "--body", help="正文（与位置参数二选一）"),
    tags: List[str] = typer.Option([], "--tag", help="标签，可重复"),
) -> None:
    """快速记一篇笔记。"""
    content = body if body is not None else " ".join(text).strip()
    if not content:
        raise typer.BadParameter("正文不能为空")
    data = state.client().post("/api/notes", {"title": title, "summary": content, "tags": tags or None})
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"#{data.get('id')} 已记录：{item.get('title')}")


@app.command("rm")
def remove(note_id: int = typer.Argument(...)) -> None:
    """删除笔记。"""
    state.client().delete(f"/api/notes/{note_id}")
    render.ok(f"#{note_id} 已删除")
