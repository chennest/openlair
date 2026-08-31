"""运行态：根回调写入 flag，子命令读（typer 的 ctx 传不到 `add_typer` 的叶子命令）。

测试通过改写模块级 `_transport`（`httpx.MockTransport`）注入假后端，再调 `reset()`。
"""

from __future__ import annotations

from typing import Any

import httpx

from laircli.client import ApiClient
from laircli.config import Settings, resolve

_flags: dict[str, Any] = {}
_transport: httpx.BaseTransport | None = None
_settings: Settings | None = None
_client: ApiClient | None = None


def set_flags(**kwargs: Any) -> None:
    _flags.update(kwargs)


def settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = resolve(**_flags)
    return _settings


def client() -> ApiClient:
    global _client
    if _client is None:
        _client = ApiClient(settings(), transport=_transport)
    return _client


def is_json() -> bool:
    return settings().json_out


def verbose() -> bool:
    """根回调的 -v，不触发配置解析（`lair init` 校验 Key 时要用）。"""
    return bool(_flags.get("verbose"))


def reset() -> None:
    global _settings, _client
    _settings = None
    _client = None
