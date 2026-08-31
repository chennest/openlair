"""typer 根应用：全局 flag 落到 `state`，子命令统一读取。

全局 flag 必须写在子命令之前（`lair --json ledger list`），或设 `LAIRCLI_JSON=1`。
"""

from __future__ import annotations

import sys
from typing import Optional

import typer

from laircli import render, state
from laircli.commands import books, calendar, habits, keys, ledger, notes, overview, setup, todo
from laircli.config import env_json
from laircli.errors import CliError

app = typer.Typer(
    name="lair",
    help="OpenLair 命令行客户端：凭 API Key 访问后端 /api（记账 / 待办 / 日程 / 笔记 / 习惯）。",
    no_args_is_help=True,
)


@app.callback()
def _root(
    json_out: bool = typer.Option(False, "--json", help="输出纯 JSON，便于管道给 jq"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="覆盖后端地址（不落盘）"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="覆盖 API Key（不落盘）"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="把请求概要走 stderr 打出来"),
) -> None:
    state.set_flags(base_url=base_url, api_key=api_key, json_out=json_out, verbose=verbose)
    render.configure(quiet=json_out or env_json(), verbose=verbose)


app.command(name="init")(setup.init)
app.command(name="whoami")(setup.whoami)
app.command(name="api")(setup.api)
app.command(name="overview")(overview.show)
app.add_typer(ledger.app, name="ledger")
app.add_typer(books.app, name="book")
app.add_typer(todo.app, name="todo")
app.add_typer(calendar.app, name="cal")
app.add_typer(notes.app, name="note")
app.add_typer(habits.app, name="habit")
app.add_typer(keys.app, name="keys")
app.add_typer(setup.app, name="config")


def _argv_has_undecodable_bytes() -> bool:
    """Windows 上 argv 按本地代码页解码失败时会留下 PEP 383 代理转义字符（\\udc80-\\udcff）。"""
    return any("\udc80" <= ch <= "\udcff" for arg in sys.argv[1:] for ch in arg)


def main() -> None:
    """控制台入口：把领域异常翻译成退出码，stdout 只留正常输出。"""
    render.ensure_utf8()
    if _argv_has_undecodable_bytes():
        render.warn("命令行里的中文未被正确解码（可能是 GBK 代码页）—— 设 PYTHONUTF8=1 或改用 UTF-8 代码页后重试。")
    try:
        app()
    except CliError as exc:
        render.fail(str(exc))
        raise SystemExit(exc.exit_code) from None
