"""客户端：信封解包与两种错误形状的归一。"""

from __future__ import annotations

import json

import httpx
import pytest

from laircli.client import ApiClient
from laircli.config import Settings
from laircli.errors import CliError


def make_client(handler) -> ApiClient:
    settings = Settings(
        api_key="ol_test", base_url="http://testserver", book_id=None, json_out=False, verbose=False, user=""
    )
    return ApiClient(settings, transport=httpx.MockTransport(handler))


def ok(payload) -> httpx.Response:
    return httpx.Response(200, json={"code": 200, "message": "成功", "data": payload})


def test_sends_api_key_header_and_unwraps_data():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["header"] = request.headers.get("X-API-Key")
        seen["url"] = str(request.url)
        return ok([{"id": 1}])

    data = make_client(handler).get("/api/books", {"page": 2, "skip": None})
    assert seen["header"] == "ol_test"
    assert data == [{"id": 1}]
    assert "page=2" in seen["url"]
    assert "skip" not in seen["url"]  # None 参数不下发


def test_envelope_error_becomes_cli_error_with_backend_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": 400, "message": "缺少账本，请先创建账本", "data": None})

    with pytest.raises(CliError, match=r"\[400\] 缺少账本"):
        make_client(handler).get("/api/ledger")


def test_401_carries_a_repair_hint():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"code": 401, "message": "未登录或登录已过期，请重新登录", "data": None})

    with pytest.raises(CliError, match="lair init"):
        make_client(handler).get("/api/auth/me")


def test_422_has_no_envelope_and_falls_back_to_detail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": [{"type": "greater_than", "loc": ["query", "pageSize"], "msg": "Input should be greater than 0", "input": "0"}]},
        )

    with pytest.raises(CliError, match=r"pageSize: Input should be greater than 0"):
        make_client(handler).get("/api/ledger", {"pageSize": 0})


def test_response_without_envelope_is_passed_through():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})

    assert make_client(handler).get("/healthz/live") == {"status": "ok"}


def test_unparseable_error_body_still_reports_status():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="<html>bad gateway</html>")

    with pytest.raises(CliError, match=r"\[502\]"):
        make_client(handler).get("/api/overview")


def test_connection_failure_is_not_reported_as_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(CliError, match="连不上"):
        make_client(handler).get("/api/books")


def test_raw_keeps_the_whole_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        return ok({"ok": True})

    payload = make_client(handler).raw("POST", "/api/books/1/leave", {"a": 1})
    assert json.loads(json.dumps(payload)) == {"code": 200, "message": "成功", "data": {"ok": True}}
