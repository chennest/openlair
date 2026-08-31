"""输出层：`--json` 时 stdout 只留纯 JSON，人类提示一律让路（走 stderr 或静默）。"""

from __future__ import annotations

import json
import sys
from typing import Any, Iterable, Sequence

from rich import box
from rich.console import Console
from rich.table import Table

_stdout = Console(highlight=False)
_stderr = Console(stderr=True, highlight=False)
_quiet = False
_verbose = False


def configure(quiet: bool, verbose: bool) -> None:
    """由根回调调用：quiet=JSON 模式下抑制人类提示。"""
    global _quiet, _verbose
    _quiet, _verbose = quiet, verbose


def ensure_utf8() -> None:
    """Windows 控制台默认 GBK，会把中文帮助和 `--json` 输出写成乱码 —— 入口统一切 UTF-8。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass


def as_json(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


def table(headers: Sequence[tuple[str, str]], rows: Iterable[Sequence[Any]]) -> None:
    data = [list(r) for r in rows]
    if not data:
        _stdout.print("[dim]（空）[/dim]")
        return
    grid = Table(box=box.SIMPLE_HEAVY, header_style="bold dim", pad_edge=False)
    for title, justify in headers:
        grid.add_column(title, justify=justify)  # type: ignore[arg-type]
    for row in data:
        grid.add_row(*[_cell(c) for c in row])
    _stdout.print(grid)


def _cell(value: Any) -> str:
    if value is None or value == "":
        return "-"
    return str(value)


def empty(message: str) -> None:
    if not _quiet:
        _stdout.print(f"[dim]{message}[/dim]")


def hint(message: str) -> None:
    """上下文提示（当前账本之类），JSON 模式下不打扰 stdout。"""
    if not _quiet:
        _stdout.print(f"[dim]{message}[/dim]")


def ok(message: str) -> None:
    _stdout.print(f"[green]{message}[/green]")


def warn(message: str) -> None:
    _stderr.print(f"[yellow]{message}[/yellow]")


def fail(message: str) -> None:
    _stderr.print(f"[red]{message}[/red]")


def log(message: str) -> None:
    """不带样式的正文（笔记详情等）。"""
    _stdout.print(message)


def debug(message: str) -> None:
    if _verbose:
        _stderr.print(f"[dim]» {message}[/dim]")
