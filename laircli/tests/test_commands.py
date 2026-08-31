"""命令端到端：假后端 + 真实 `lair` 入口，校验发出的请求体和拿到的退出码。"""

from __future__ import annotations

import json
from typing import Any, Callable

import httpx

from laircli.config import load, save
from samples import BOOKS, CATEGORIES, EVENTS, FAKE_KEY, HABITS, KEYS, LEDGER_LIST, ME, NOTES, TODOS, TX, bare, fail, ok


def router(routes: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    """按 "METHOD /path" 放行；没列出来的请求直接让用例失败。"""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        calls.append(key)
        hit = routes.get(key)
        if hit is None:
            raise AssertionError(f"未预期的请求：{key}（已发生 {calls}）")
        return hit(request) if callable(hit) else hit

    handler.calls = calls  # type: ignore[attr-defined]
    return handler


def captures(into: dict, key: str, response: httpx.Response):
    def handler(request: httpx.Request) -> httpx.Response:
        into[key] = json.loads(request.content)
        return response

    return handler


LEDGER_READ = {"GET /api/books": ok(BOOKS), "GET /api/ledger/categories": ok(CATEGORIES)}


def test_ledger_add_sends_resolved_category_id(configured, serve, invoke):
    sent: dict = {}
    serve(
        router(
            {
                **LEDGER_READ,
                "POST /api/ledger": captures(sent, "body", ok({"id": 99, "item": TX})),
            }
        )
    )
    code, out = invoke("ledger", "add", "38.5", "-c", "餐饮", "-n", "午饭")
    assert code == 0
    assert sent["body"] == {
        "type": "支出",
        "amount": 38.5,
        "bookId": 1,
        "categoryId": 1,
        "date": None,
        "note": "午饭",
    }
    assert "餐饮" in out and "#99" in out


def test_ledger_add_infers_income_from_category(configured, serve, invoke):
    sent: dict = {}
    income = {**TX, "type": "收入", "categoryId": 11, "category": "工资"}
    serve(router({**LEDGER_READ, "POST /api/ledger": captures(sent, "body", ok({"id": 100, "item": income}))}))
    code, out = invoke("ledger", "add", "12000", "-c", "工资")
    assert code == 0
    assert sent["body"]["type"] == "收入"
    assert sent["body"]["categoryId"] == 11
    assert "工资" in out


def test_unknown_category_fails_before_writing(configured, serve, invoke):
    handler = router(LEDGER_READ)  # 注意：没有放行 POST /api/ledger
    serve(handler)
    code, out = invoke("ledger", "add", "30", "-c", "夜宵")
    assert code == 1
    assert "夜宵" in out and "餐饮" in out  # 报错时把可选分类列出来
    assert "POST /api/ledger" not in handler.calls


def test_ledger_add_uses_configured_book(configured, serve, invoke):
    save({"book_id": 2})
    sent: dict = {}
    serve(router({**LEDGER_READ, "POST /api/ledger": captures(sent, "body", ok({"id": 1, "item": TX}))}))
    code, _ = invoke("ledger", "add", "10", "-c", "交通")
    assert code == 0
    assert sent["body"]["bookId"] == 2


def test_cli_book_flag_beats_config(configured, serve, invoke):
    save({"book_id": 2})
    sent: dict = {}
    serve(router({**LEDGER_READ, "POST /api/ledger": captures(sent, "body", ok({"id": 1, "item": TX}))}))
    code, _ = invoke("ledger", "add", "10", "-c", "交通", "-b", "1")
    assert code == 0
    assert sent["body"]["bookId"] == 1


def test_auto_selected_book_is_announced(configured, serve, invoke):
    serve(router({**LEDGER_READ, "POST /api/ledger": ok({"id": 1, "item": TX})}))
    code, out = invoke("ledger", "add", "10", "-c", "交通")
    assert code == 0
    assert "默认账本" in out and "lair book use" in out


def test_no_category_hint_says_it_landed_in_other(configured, serve, invoke):
    serve(router({**LEDGER_READ, "POST /api/ledger": ok({"id": 1, "item": {**TX, "category": "其他"}})}))
    code, out = invoke("ledger", "add", "10")
    assert code == 0
    assert "其他" in out and "-c" in out


def test_ledger_list_json_is_machine_readable(configured, serve, invoke):
    served: dict = {}

    def ledger(request: httpx.Request) -> httpx.Response:
        served.update(dict(request.url.params))
        return ok(LEDGER_LIST)

    serve(router({"GET /api/books": ok(BOOKS), "GET /api/ledger": ledger}))
    code, out = invoke("--json", "ledger", "list", "-t", "expense", "--page-size", "5")
    assert code == 0
    assert json.loads(out)["transactions"][0]["note"] == "午饭"
    assert served == {"bookId": "1", "type": "支出", "page": "1", "pageSize": "5"}


def test_ledger_list_shows_summary_line(configured, serve, invoke):
    serve(router({"GET /api/books": ok(BOOKS), "GET /api/ledger": ok(LEDGER_LIST)}))
    code, out = invoke("ledger", "list")
    assert code == 0
    assert "餐饮" in out and "结余" in out and "预算" in out


def test_missing_book_on_server_side_is_reported(configured, serve, invoke):
    serve(router({"GET /api/books": ok([])}))
    code, out = invoke("ledger", "list")
    assert code == 1
    assert "lair book create" in out


def test_backend_business_error_becomes_exit_1(configured, serve, invoke):
    serve(router({"DELETE /api/ledger/999999": fail(404, "流水不存在")}))
    code, out = invoke("ledger", "rm", "999999")
    assert code == 1
    assert "流水不存在" in out


def test_validation_error_without_envelope_is_still_readable(configured, serve, invoke):
    serve(router({"DELETE /api/ledger/1": bare({"detail": [{"loc": ["path", "transaction_id"], "msg": "int_parsing", "type": "x"}]})}))
    code, out = invoke("ledger", "rm", "1")
    assert code == 1
    assert "参数不合法" in out and "transaction_id" in out


def test_todo_done_puts_done_true(configured, serve, invoke):
    sent: dict = {}
    serve(router({"PUT /api/todo/1": captures(sent, "body", ok({"item": TODOS[0]}))}))
    code, out = invoke("todo", "done", "1")
    assert code == 0
    assert sent["body"] == {"done": True}
    assert "已完成" in out


def test_todo_list_open_only_filters_locally(configured, serve, invoke):
    serve(router({"GET /api/todo": ok({"todos": TODOS})}))
    code, out = invoke("--json", "todo", "list", "--open")
    assert code == 0
    assert [t["id"] for t in json.loads(out)] == [1]


def test_todo_add_maps_quadrant_number(configured, serve, invoke):
    sent: dict = {}
    serve(router({"POST /api/todo": captures(sent, "body", ok({"id": 3, "item": {**TODOS[0], "id": 3}}))}))
    code, _ = invoke("todo", "add", "写周报", "-q", "1")
    assert sent["body"] == {"text": "写周报", "quadrant": "重要紧急"}


def test_habit_check_marks_done(configured, serve, invoke):
    sent: dict = {}
    serve(router({"PUT /api/habits/1": captures(sent, "body", ok({"item": {**HABITS[0], "done": True}}))}))
    code, out = invoke("habit", "check", "1")
    assert code == 0 and sent["body"] == {"done": True}
    assert "已打卡" in out


def test_habit_list_renders_week_bar(configured, serve, invoke):
    serve(router({"GET /api/habits": ok({"habits": HABITS})}))
    code, out = invoke("habit", "list")
    assert code == 0
    assert "▰▰▱" in out


def test_cal_list_filters_by_day(configured, serve, invoke):
    serve(router({"GET /api/calendar": ok({"events": EVENTS})}))
    code, out = invoke("--json", "cal", "list", "--day", "2026-09-02")
    assert code == 0
    assert [e["id"] for e in json.loads(out)] == [1]


def test_note_add_sends_positional_text_as_summary(configured, serve, invoke):
    sent: dict = {}
    serve(router({"POST /api/notes": captures(sent, "body", ok({"id": 2, "item": {**NOTES[0], "id": 2}}))}))
    code, _ = invoke("note", "add", "定了", "Q4", "目标", "--title", "周会", "--tag", "工作")
    assert code == 0
    assert sent["body"] == {"title": "周会", "summary": "定了 Q4 目标", "tags": ["工作"]}


def test_overview_renders_all_sections(configured, serve, invoke):
    serve(
        router(
            {
                "GET /api/overview": ok(
                    {
                        "monthExpense": {"amount": 1234.5, "budget": 5000.0, "trend": 12.3},
                        "todos": [{"text": "写周报", "time": "今天", "tag": "重要紧急", "tagClass": "red"}],
                        "upcoming": [{"text": "体检", "date": "2026-09-02 09:00", "tag": "日程", "tagClass": "green"}],
                        "habits": [{"name": "早睡", "done": True}],
                    }
                )
            }
        )
    )
    code, out = invoke("overview")
    assert code == 0
    for token in ("本月支出", "写周报", "体检", "早睡"):
        assert token in out


def test_keys_create_prints_plaintext_once(configured, serve, invoke):
    serve(router({"POST /api/keys": ok({"apiKey": FAKE_KEY, "item": KEYS[1]})}))
    code, out = invoke("keys", "create", "临时")
    assert code == 0
    assert FAKE_KEY in out


def test_config_show_never_prints_the_full_key(configured, invoke):
    code, out = invoke("config", "show")
    assert code == 0
    assert FAKE_KEY not in out
    assert FAKE_KEY[:12] + "…" in out


def test_keys_revoke_refuses_without_confirmation(configured, serve, invoke):
    serve(router({"GET /api/keys": ok({"keys": KEYS}), "DELETE /api/keys/2": ok({"ok": True})}))
    code, out = invoke("keys", "revoke", "2")
    assert code != 0  # typer.confirm 拿不到输入会中止
    assert "确认撤销" in out


def test_keys_revoke_self_warns(configured, serve, invoke):
    serve(router({"GET /api/keys": ok({"keys": KEYS}), "DELETE /api/keys/1": ok({"ok": True})}))
    code, out = invoke("keys", "revoke", "1", "-y")
    assert code == 0
    assert "当前 CLI 在用" in out


def test_book_use_persists_after_validating(configured, serve, invoke):
    serve(router({"GET /api/books": ok(BOOKS)}))
    code, out = invoke("book", "use", "2")
    assert code == 0
    assert load().get("book_id") == 2
    code, out = invoke("book", "use", "99")
    assert code == 1 and "不存在" in out


def test_whoami_uses_the_stored_key(configured, serve, invoke):
    seen: dict = {}

    def me(request: httpx.Request) -> httpx.Response:
        seen["key"] = request.headers.get("X-API-Key")
        return ok(ME)

    serve(router({"GET /api/auth/me": me}))
    code, out = invoke("whoami")
    assert code == 0
    assert seen["key"] == FAKE_KEY and "test1@openlair.dev" in out


def test_api_escape_hatch_returns_the_envelope(configured, serve, invoke):
    sent: dict = {}
    serve(router({"POST /api/books/1/leave": captures(sent, "body", ok({"ok": True}))}))
    code, out = invoke("api", "POST", "/api/books/1/leave", "--data", '{"x": 1}')
    assert code == 0
    assert json.loads(out) == {"code": 200, "message": "成功", "data": {"ok": True}}
    assert sent["body"] == {"x": 1}


def test_mojibake_argv_is_flagged_not_fatal(configured, serve, invoke):
    """Windows 代码页会把中文参数解成代理转义字符 —— 提示但不阻断。"""
    serve(router({"GET /api/books": ok(BOOKS), "GET /api/ledger": ok(LEDGER_LIST)}))
    bad = "终端".encode("gbk").decode("utf-8", "surrogateescape")
    code, out = invoke("ledger", "list", "-k", bad)
    assert code == 1  # 不是 traceback，而是可执行的提示 + 退出码 1
    assert "PYTHONUTF8" in out


def test_unconfigured_exits_3_and_points_at_init(invoke):
    code, out = invoke("whoami")
    assert code == 3
    assert "lair init" in out
