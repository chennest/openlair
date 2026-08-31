"""解析层：类型/象限别名、日期别名、账本优先级、分类名 → id。"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import pytest

from laircli.client import ApiClient
from laircli.config import Settings
from laircli.errors import CliError
from laircli.resolver import map_quadrant, map_type, parse_date, resolve_book, resolve_category

from samples import BOOKS, CATEGORIES

CATEGORIES_BODY = {"code": 200, "message": "成功", "data": CATEGORIES}
BOOKS_BODY = {"code": 200, "message": "成功", "data": BOOKS}


def make_client(handler) -> ApiClient:
    settings = Settings(
        api_key="ol_test", base_url="http://testserver", book_id=None, json_out=False, verbose=False, user=""
    )
    return ApiClient(settings, transport=httpx.MockTransport(handler))


def books_client() -> ApiClient:
    return make_client(lambda request: httpx.Response(200, json=BOOKS_BODY))


def cats_client() -> ApiClient:
    def handler(request: httpx.Request) -> httpx.Response:
        tx_type = request.url.params.get("type")
        rows = [c for c in CATEGORIES if not tx_type or c["type"] == tx_type]
        return httpx.Response(200, json={**CATEGORIES_BODY, "data": rows})

    return make_client(handler)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("expense", "支出"),
        ("EXPENSE", "支出"),
        ("-", "支出"),
        ("支出", "支出"),
        ("income", "收入"),
        ("+", "收入"),
        ("收入", "收入"),
    ],
)
def test_map_type_accepts_aliases(raw, expected):
    # 后端会把任何非「收入」的值悄悄归成「支出」，所以非法值必须在这里挡住。
    assert map_type(raw) == expected


@pytest.mark.parametrize("raw", ["", "maybe", "balance", "支出/收入"])
def test_map_type_rejects_unknown(raw):
    with pytest.raises(CliError, match="类型不合法"):
        map_type(raw)


def test_map_quadrant_accepts_number_and_prefix():
    assert map_quadrant("1") == "重要紧急"
    assert map_quadrant("4") == "不重要不紧急"
    assert map_quadrant("重要不紧急") == "重要不紧急"
    with pytest.raises(CliError, match="象限不合法"):
        map_quadrant("5")


def test_parse_date_accepts_iso_and_chinese_aliases():
    today = date.today()
    assert parse_date("2026-08-31", "--date") == "2026-08-31"
    assert parse_date("今天", "--date") == today.isoformat()
    assert parse_date("昨天", "--date") == (today - timedelta(days=1)).isoformat()
    with pytest.raises(CliError, match="YYYY-MM-DD"):
        parse_date("31/08/2026", "--date")


def test_resolve_book_prefers_flag_then_settings():
    assert resolve_book(books_client(), 2, 1)[0].id == 2
    assert resolve_book(books_client(), None, 2)[0].id == 2


def test_resolve_book_falls_back_to_first_personal_and_says_so():
    book, explicit = resolve_book(books_client(), None, None)
    assert (book.id, book.type, explicit) == (1, "personal", False)


def test_resolve_book_rejects_unknown_id():
    with pytest.raises(CliError, match="不存在或你已不在其中"):
        resolve_book(books_client(), 99, None)


def test_resolve_book_without_any_book():
    empty = make_client(lambda request: httpx.Response(200, json={**BOOKS_BODY, "data": []}))
    with pytest.raises(CliError, match="lair book create"):
        resolve_book(empty, None, None)


def test_resolve_category_by_name_within_type():
    assert resolve_category(cats_client(), "支出", "餐饮").id == 1
    assert resolve_category(cats_client(), "收入", "工资").type == "收入"


def test_resolve_category_infers_type_when_not_given():
    picked = resolve_category(cats_client(), None, "工资")
    assert (picked.id, picked.type) == (11, "收入")


def test_resolve_category_by_id_must_match_side():
    assert resolve_category(cats_client(), None, "11").name == "工资"
    with pytest.raises(CliError, match="不在「支出」可选分类里"):
        resolve_category(cats_client(), "支出", "11")


def test_resolve_category_ambiguous_prefix_lists_candidates():
    with pytest.raises(CliError, match="有歧义"):
        resolve_category(cats_client(), None, "其他")


def test_resolve_category_unknown_names_suggest_options():
    with pytest.raises(CliError, match="餐饮"):
        resolve_category(cats_client(), None, "夜宵")


def test_resolve_category_none_is_passthrough():
    assert resolve_category(cats_client(), None, None) is None
