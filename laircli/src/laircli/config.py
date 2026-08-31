"""`~/.laircli/config.toml`：API Key 落盘 + 三级解析（flag > env > 文件）。

安全约定：明文 Key 只进文件，任何输出/报错一律走 `mask()`；Windows 的 `chmod` 只切只读位
（ACL 不变），所以真正的保护是"永不打印"，不是文件权限。
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from laircli.errors import CliError, NotConfigured

DEFAULT_BASE_URL = "https://lair.lcc007.top"
FIELDS = ("api_key", "base_url", "book_id", "user")


def config_path() -> Path:
    """配置文件路径；`LAIRCLI_CONFIG` 用于测试与多环境切换。"""
    override = os.environ.get("LAIRCLI_CONFIG")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    root = Path(xdg) / "laircli" if xdg else Path.home() / ".laircli"
    return root / "config.toml"


def load() -> dict:
    path = config_path()
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as fh:
            return dict(tomllib.load(fh))
    except tomllib.TOMLDecodeError as exc:
        raise CliError(f"配置文件不可解析（{path}）：{exc}") from exc


def save(updates: dict) -> Path:
    """合并写入配置文件。"""
    return _write({**load(), **updates})


def _write(values: dict) -> Path:
    body = "".join(f"{k} = {_dump(values[k])}\n" for k in FIELDS if values.get(k) is not None)
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def remove_keys(*keys: str) -> None:
    data = {k: v for k, v in load().items() if k not in keys}
    path = config_path()
    if not data:
        path.unlink(missing_ok=True)
        return
    _write(data)


def reset() -> None:
    """删除配置文件（`lair init` 校验失败时回退用）。"""
    config_path().unlink(missing_ok=True)


def _dump(value: object) -> str:
    # json.dumps 的转义集是 TOML 基本字符串的子集，Windows 路径反斜杠不会写坏文件。
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def env_json() -> bool:
    """`LAIRCLI_JSON=1` 等价于全局 `--json`（子命令参数位置受限时更方便）。"""
    return (os.environ.get("LAIRCLI_JSON") or "").lower() in {"1", "true", "yes"}


def mask(api_key: str) -> str:
    """与后端 DTO 一致：只暴露前 12 字符（`ol_` + 随机串前缀）。"""
    if len(api_key) <= 12:
        return "***"
    return f"{api_key[:12]}…"


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    book_id: int | None
    json_out: bool
    verbose: bool
    user: str


def resolve(
    api_key: str | None = None,
    base_url: str | None = None,
    book_id: int | None = None,
    json_out: bool = False,
    verbose: bool = False,
) -> Settings:
    data = load()
    key = (api_key or os.environ.get("OPENLAIR_API_KEY") or data.get("api_key") or "").strip()
    if not key:
        raise NotConfigured("尚未配置 API Key：先运行 lair init（或设置环境变量 OPENLAIR_API_KEY）")
    url = (
        base_url
        or os.environ.get("OPENLAIR_BASE_URL")
        or data.get("base_url")
        or DEFAULT_BASE_URL
    ).rstrip("/")
    env_book = os.environ.get("OPENLAIR_BOOK_ID")
    chosen = book_id
    if chosen is None:
        chosen = _as_int(env_book, "OPENLAIR_BOOK_ID") if env_book else _as_int(data.get("book_id"), "book_id")
    json_flag = json_out or env_json()
    return Settings(
        api_key=key,
        base_url=url,
        book_id=chosen,
        json_out=bool(json_flag),
        verbose=verbose,
        user=str(data.get("user") or ""),
    )


def _as_int(value: object, label: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except ValueError:
        raise CliError(f"{label} 需为整数，当前为 {value!r}") from None
