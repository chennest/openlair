"""`lair book`：账本列表 / 默认账本 / 创建 / 邀请 / 回收站。"""

from __future__ import annotations

from typing import Optional

import typer

from laircli import config, render, resolver, state
from laircli.errors import CliError

app = typer.Typer(help="账本：列表 / 切换默认 / 创建 / 邀请 / 回收站", no_args_is_help=True)

_TYPE_LABEL = {"personal": "个人", "shared": "共享"}


def _books() -> list[dict]:
    return state.client().get("/api/books") or []


@app.command("list")
def list_() -> None:
    """我参与的账本。"""
    data = _books()
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("名称", "left"), ("类型", "left"), ("成员", "left")],
        [
            [
                b.get("id"),
                b.get("name"),
                _TYPE_LABEL.get(str(b.get("type")), b.get("type")),
                "、".join(str((m.get("user") or {}).get("name") or "?") for m in (b.get("members") or [])) or "-",
            ]
            for b in data
        ],
    )
    render.hint("设默认账本：lair book use <id>")


@app.command("create")
def create(
    name: str = typer.Argument(..., help="账本名称"),
    type_: str = typer.Option("personal", "--type", "-t", help="personal / shared"),
) -> None:
    """新建账本（建的人自动成为 owner）。"""
    data = state.client().post("/api/books", {"name": name, "type": type_})
    book = (data or {}).get("book") or {}
    if state.is_json():
        render.as_json(data)
        return
    render.ok(f"账本 #{book.get('id')} {book.get('name')} 已创建")
    render.hint(f"设为默认：lair book use {book.get('id')}")


@app.command("use")
def use(book_id: int = typer.Argument(..., help="账本 id")) -> None:
    """把某个账本设为默认（写入配置文件）。"""
    hit = next((b for b in _books() if int(b.get("id") or -1) == book_id), None)
    if hit is None:
        raise CliError(f"账本 {book_id} 不存在或你已不在其中：lair book list 看可选")
    config.save({"book_id": book_id})
    state.reset()
    render.ok(f"默认账本已切换为 #{book_id} {hit.get('name')}")


@app.command("current")
def current(book: Optional[int] = typer.Option(None, "--book", "-b")) -> None:
    """显示当前生效的账本及来源。"""
    target, explicit = resolver.resolve_book(state.client(), book, state.settings().book_id)
    source = "命令行 --book / 配置" if explicit else "自动取首个个人账本"
    if state.is_json():
        render.as_json({"id": target.id, "name": target.name, "type": target.type, "source": source})
        return
    render.log(f"当前账本：#{target.id} {target.name}（{_TYPE_LABEL.get(target.type, target.type)}）· 来源：{source}")


@app.command("join")
def join(code: str = typer.Argument(..., help="8 位邀请码")) -> None:
    """用邀请码加入共享账本（成为 editor）。"""
    data = state.client().post("/api/books/join", {"code": code})
    book = (data or {}).get("book") or {}
    if state.is_json():
        render.as_json(data)
        return
    render.ok(f"已加入账本 #{book.get('id')} {book.get('name')}")


@app.command("invite")
def invite(
    book_id: int = typer.Argument(...),
    rotate: bool = typer.Option(False, "--rotate", help="生成/重置邀请码（owner 权限）"),
) -> None:
    """查看（默认）或重置共享账本的邀请码。"""
    path = f"/api/books/{book_id}/invite"
    data = state.client().post(path) if rotate else state.client().get(path)
    code = (data or {}).get("code")
    if state.is_json():
        render.as_json(data)
        return
    render.log(f"#{book_id} 邀请码：{code}" if code else f"#{book_id} 尚无邀请码（加 --rotate 生成）")


@app.command("delete")
def delete(book_id: int = typer.Argument(...)) -> None:
    """删除账本（软删进回收站，可 lair book restore 找回；owner 权限）。"""
    state.client().delete(f"/api/books/{book_id}")
    render.ok(f"账本 #{book_id} 已移入回收站（lair book trash 查看）")


@app.command("trash")
def trash() -> None:
    """回收站里的账本。"""
    data = state.client().get("/api/books/trash") or []
    if state.is_json():
        render.as_json(data)
        return
    render.table(
        [("ID", "right"), ("名称", "left"), ("类型", "left"), ("成员", "right")],
        [[b.get("id"), b.get("name"), _TYPE_LABEL.get(str(b.get("type")), b.get("type")), len(b.get("members") or [])] for b in data],
    )
    if data:
        render.hint("找回：lair book restore <id>")


@app.command("restore")
def restore(book_id: int = typer.Argument(...)) -> None:
    """从回收站恢复账本。"""
    state.client().post(f"/api/books/{book_id}/restore")
    render.ok(f"账本 #{book_id} 已恢复")
