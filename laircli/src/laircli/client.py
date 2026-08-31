"""HTTP 客户端：`X-API-Key` 头 + `{code,message,data}` 信封解包。

后端的失败形状有两种：业务错误走统一信封（HTTP 状态 == code），而参数校验 422 是 FastAPI
默认的裸 `{"detail":[...]}`（`app/core/envelope.py` 未注册 RequestValidationError handler）。
这里统一归一成一个 `CliError` 文案。
"""

from __future__ import annotations

from typing import Any

import httpx

from laircli.config import Settings
from laircli.errors import CliError
from laircli.render import debug


class ApiClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._http = httpx.Client(
            base_url=settings.base_url,
            headers={"X-API-Key": settings.api_key},
            timeout=15.0,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: dict | None = None) -> Any:
        return self.request("POST", path, json_body=body)

    def put(self, path: str, body: dict | None = None) -> Any:
        return self.request("PUT", path, json_body=body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> Any:
        clean = {k: v for k, v in (params or {}).items() if v is not None}
        resp = self._send(method, path, params=clean or None, json=json_body)
        debug(f"{method} {path} → {resp.status_code}")
        payload = _json_or_none(resp)
        if resp.is_success:
            if isinstance(payload, dict) and "data" in payload:
                return payload["data"]
            return payload
        raise CliError(_error_message(resp, payload))

    def raw(self, method: str, path: str, body: Any = None) -> Any:
        """`lair api` 逃生口：原样返回响应信封，便于试未封装的接口。"""
        resp = self._send(method, path, json=body)
        debug(f"{method} {path} → {resp.status_code}")
        payload = _json_or_none(resp)
        if not resp.is_success:
            raise CliError(_error_message(resp, payload))
        return payload

    def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            return self._http.request(method, path, **kwargs)
        except UnicodeEncodeError as exc:
            raise CliError(
                f"命令行参数里有未正确解码的中文字符（{exc}）—— 设 PYTHONUTF8=1 或改用 UTF-8 代码页"
            ) from None
        except httpx.HTTPError as exc:
            raise CliError(f"连不上 {self.settings.base_url}：{exc}") from exc


def _json_or_none(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return None


def _error_message(resp: httpx.Response, payload: Any) -> str:
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str) and message:
            suffix = ""
            if resp.status_code == 401:
                suffix = "（API Key 无效或已被撤销：lair config show 核对，或重新 lair init）"
            return f"[{resp.status_code}] {message}{suffix}"
        detail = payload.get("detail")
        if isinstance(detail, list) and detail:
            return "[422] 参数不合法：" + "；".join(_detail_text(item) for item in detail)
        if isinstance(detail, str) and detail:
            return f"[{resp.status_code}] {detail}"
    return f"[{resp.status_code}] 响应无法解析"


def _detail_text(item: Any) -> str:
    if not isinstance(item, dict):
        return str(item)
    loc = ".".join(str(p) for p in (item.get("loc") or [])[1:])
    msg = item.get("msg") or item.get("type") or "字段不合法"
    return f"{loc}: {msg}" if loc else str(msg)
