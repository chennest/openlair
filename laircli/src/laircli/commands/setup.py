"""配置与逃生口：`lair init` / `lair config` / `lair whoami` / `lair api`。"""

from __future__ import annotations

import json
from typing import Optional

import typer

from laircli import config, render, state
from laircli.client import ApiClient
from laircli.config import DEFAULT_BASE_URL, Settings
from laircli.errors import CliError

app = typer.Typer(help="配置管理", no_args_is_help=True)


def init(
    api_key: str = typer.Option(
        None,
        "--api-key",
        prompt="粘贴 API Key（ol_ 开头，Web 端「API Key」页创建时只显示一次）",
        hide_input=True,
        help="直接传入 Key，跳过交互",
    ),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", prompt="后端地址", help="默认生产站点"),
) -> None:
    """把 API Key 写到 ~/.laircli/config.toml，校验通过才算配置成功。"""
    key = (api_key or "").strip()
    if not key.startswith("ol_"):
        raise CliError("这看起来不是 API Key：应以 ol_ 开头（约 46 字符）")
    url = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
    settings = Settings(
        api_key=key, base_url=url, book_id=None, json_out=False, verbose=state.verbose(), user=""
    )
    try:
        me = ApiClient(settings).get("/api/auth/me")
    except CliError:
        render.fail("Key 校验失败，未写入任何文件")
        raise
    config.save({"api_key": key, "base_url": url, "user": str(me.get("name") or "")})
    render.hint(f"配置已写入 {config.config_path()}")
    render.ok(f"已连接 {url} —— 你好，{me.get('name')}（{me.get('email')}）")
    render.hint("下一步：lair book list 看一下账本，再 lair book use <id> 设成默认账本")


def whoami() -> None:
    """当前 Key 属于哪个用户。"""
    me = state.client().get("/api/auth/me")
    if state.is_json():
        render.as_json(me)
        return
    render.table(
        [("字段", "left"), ("值", "left")],
        [
            ["id", me.get("id")],
            ["昵称", me.get("name")],
            ["邮箱", me.get("email") or "-"],
            ["注册于", me.get("createdAt")],
        ],
    )


def api(
    method: str = typer.Argument(..., help="GET / POST / PUT / DELETE"),
    path: str = typer.Argument(..., help="以 / 开头的接口路径，如 /api/books"),
    data: Optional[str] = typer.Option(None, "--data", help="JSON 请求体"),
) -> None:
    """原样调用任意接口（覆盖成员管理、convert、purge、转写等未封装能力）。"""
    if not path.startswith("/"):
        hint = (
            "；路径看起来被 Git Bash 改写了 —— 用 `MSYS2_ARG_CONV_EXCL='*' lair api GET /api/...`，或改用 PowerShell"
            if "/api/" in path
            else ""
        )
        raise CliError(f"path 必须以 / 开头，例如 /api/books{hint}")
    body = None
    if data:
        try:
            body = json.loads(data)
        except json.JSONDecodeError as exc:
            raise CliError(f"--data 不是合法 JSON：{exc}") from None
    render.as_json(state.client().raw(method.upper(), path, body))


@app.command("show")
def config_show() -> None:
    """显示当前配置（Key 只展示前缀）。"""
    path = config.config_path()
    data = config.load()
    key = str(data.get("api_key") or "")
    rows = [
        ["配置文件", str(path) + ("" if path.is_file() else "（尚未创建）")],
        ["api_key", config.mask(key) if key else "（未配置）"],
        ["base_url", data.get("base_url") or config.DEFAULT_BASE_URL],
        ["book_id", data.get("book_id") or "（未设置：ledger 会自动取首个账本）"],
        ["user", data.get("user") or "-"],
    ]
    if state.is_json():
        render.as_json({r[0]: r[1] for r in rows})
        return
    render.table([("配置", "left"), ("值", "left")], rows)


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="api_key / base_url / book_id / user"),
    value: str = typer.Argument(...),
) -> None:
    """写单个配置项。"""
    if key not in config.FIELDS:
        raise CliError(f"未知配置项：{key}（可选 {'、'.join(config.FIELDS)}）")
    stored: object = value.strip()
    if key == "book_id":
        if not stored or str(stored).isdigit():
            stored = int(stored or 0) or None
        else:
            raise CliError("book_id 需为整数")
    if key == "api_key" and not str(stored).startswith("ol_"):
        raise CliError("这看起来不是 API Key：应以 ol_ 开头")
    if key == "base_url":
        stored = str(stored).rstrip("/")
    config.save({key: stored})
    state.reset()
    render.ok(f"{key} 已更新")


@app.command("unset")
def config_unset(key: str = typer.Argument(..., help="要删除的配置项")) -> None:
    """删除单个配置项（全部删完则移除文件）。"""
    if key not in config.FIELDS:
        raise CliError(f"未知配置项：{key}（可选 {'、'.join(config.FIELDS)}）")
    config.remove_keys(key)
    state.reset()
    render.ok(f"{key} 已移除")
