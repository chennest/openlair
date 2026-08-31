"""`lair keys`：API Key 列表 / 创建 / 撤销。"""

from __future__ import annotations

import typer

from laircli import config, render, state
from laircli.errors import CliError

app = typer.Typer(help="API Key 管理（每人最多 20 把有效 Key）", no_args_is_help=True)


@app.command("list")
def list_() -> None:
    """我名下有效的 API Key（只显示前缀）。"""
    data = (state.client().get("/api/keys") or {}).get("keys") or []
    if state.is_json():
        render.as_json(data)
        return
    current = str(config.load().get("api_key") or "")
    render.table(
        [("ID", "right"), ("名称", "left"), ("前缀", "left"), ("创建于", "left"), ("最后使用", "left"), ("当前", "center")],
        [
            [
                k.get("id"),
                k.get("name"),
                k.get("prefix"),
                k.get("createdAt"),
                k.get("lastUsedAt") or "从未",
                "◀" if current and k.get("prefix") == current[:12] else "",
            ]
            for k in data
        ],
    )


@app.command("create")
def create(name: str = typer.Argument(..., help="Key 名称（1-30 字，便于日后识别）")) -> None:
    """新建一把 Key —— 明文只显示这一次，请立即保存。"""
    data = state.client().post("/api/keys", {"name": name})
    if state.is_json():
        render.as_json(data)
        return
    item = data.get("item") or {}
    render.ok(f"#{item.get('id')} {item.get('name')} 已创建：")
    render.log(f"  {data.get('apiKey')}")
    render.warn("  以上明文不会再出现在任何接口里；换机器用 lair init 重新粘贴。")


@app.command("revoke")
def revoke(
    key_id: int = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", "-y", help="跳过确认"),
) -> None:
    """撤销一把 Key（立即失效，不可恢复）。"""
    items = (state.client().get("/api/keys") or {}).get("keys") or []
    hit = next((k for k in items if int(k.get("id") or -1) == key_id), None)
    if hit is None:
        raise CliError(f"Key {key_id} 不存在或已撤销：lair keys list 看可选")
    current = str(config.load().get("api_key") or "")
    is_self = bool(current) and hit.get("prefix") == current[:12]
    if is_self:
        render.warn("这把正是当前 CLI 在用的 Key —— 撤销后本机会立刻无法访问。")
    if not yes:
        typer.confirm(f"确认撤销 #{key_id} {hit.get('name')}？", abort=True)
    state.client().delete(f"/api/keys/{key_id}")
    render.ok(f"#{key_id} {hit.get('name')} 已撤销")
    if is_self:
        render.hint("本机 Key 已失效：重新 lair init，或 lair config set api_key <新 Key>")
