"""测试用样例数据：形状严格照抄后端 DTO（camelCase）。"""

from __future__ import annotations

from typing import Any

import httpx


def ok(payload: Any, status: int = 200) -> httpx.Response:
    """成功信封：后端固定 `code=200`。"""
    return httpx.Response(status, json={"code": 200, "message": "成功", "data": payload})


def fail(status: int, message: str) -> httpx.Response:
    """业务错误信封：HTTP 状态与 `code` 一致。"""
    return httpx.Response(status, json={"code": status, "message": message, "data": None})


def bare(payload: Any, status: int = 422) -> httpx.Response:
    """裸响应：模拟没有信封的 FastAPI 422。"""
    return httpx.Response(status, json=payload)


FAKE_KEY = "ol_" + "a" * 43

BOOKS: list[dict[str, Any]] = [
    {"id": 1, "name": "默认账本", "type": "personal", "members": [{"user": {"name": "我"}, "role": "owner"}]},
    {"id": 2, "name": "家庭共享", "type": "shared", "members": [{"user": {"name": "小明"}, "role": "editor"}]},
]

CATEGORIES: list[dict[str, Any]] = [
    {"id": 1, "name": "餐饮", "type": "支出", "sortOrder": 1, "isDefault": False},
    {"id": 2, "name": "交通", "type": "支出", "sortOrder": 2, "isDefault": False},
    {"id": 10, "name": "其他", "type": "支出", "sortOrder": 10, "isDefault": True},
    {"id": 11, "name": "工资", "type": "收入", "sortOrder": 11, "isDefault": False},
    {"id": 16, "name": "其他", "type": "收入", "sortOrder": 16, "isDefault": True},
]

TX: dict[str, Any] = {
    "id": 99,
    "type": "支出",
    "categoryId": 1,
    "category": "餐饮",
    "bookId": 1,
    "userId": 1,
    "userName": "我",
    "amount": 38.5,
    "date": "2026-08-31",
    "note": "午饭",
}

LEDGER_LIST: dict[str, Any] = {
    "summary": {"income": 100.0, "expense": 38.5, "balance": 61.5},
    "categoryStats": [{"categoryId": 1, "name": "餐饮", "amount": 38.5, "percent": 100.0}],
    "transactions": [TX],
    "total": 1,
    "page": 1,
    "pageSize": 20,
    "budget": 5000.0,
}

TODOS: list[dict[str, Any]] = [
    {"id": 1, "text": "写周报", "quadrant": "重要紧急", "done": False, "due": "今天", "createdAt": "", "updatedAt": ""},
    {"id": 2, "text": "交房租", "quadrant": "重要不紧急", "done": True, "due": "本周", "createdAt": "", "updatedAt": ""},
]

EVENTS: list[dict[str, Any]] = [
    {"id": 1, "title": "体检", "date": "2026-09-02", "time": "09:00", "location": "一院", "done": False, "createdAt": "", "updatedAt": ""},
    {"id": 2, "title": "旧日程", "date": "2026-08-01", "time": "10:00", "location": "", "done": True, "createdAt": "", "updatedAt": ""},
]

NOTES: list[dict[str, Any]] = [
    {"id": 1, "title": "会议记录", "summary": "定了 Q4 目标", "tags": ["工作"], "createdAt": "", "updatedAt": ""}
]

HABITS: list[dict[str, Any]] = [
    {"id": 1, "name": "早睡", "streak": 3, "done": False, "week": [True, True, False, False, False, False, False], "createdAt": "", "updatedAt": ""}
]

KEYS: list[dict[str, Any]] = [
    {"id": 1, "name": "mac", "prefix": FAKE_KEY[:12], "createdAt": "2026-08-01T00:00:00Z", "lastUsedAt": None},
    {"id": 2, "name": "临时", "prefix": "ol_bbbbbbbbbbb", "createdAt": "2026-08-02T00:00:00Z", "lastUsedAt": "2026-08-30T00:00:00Z"},
]

ME: dict[str, Any] = {"id": 1, "name": "我", "email": "test1@openlair.dev", "avatarColor": "#0071e3", "createdAt": "2026-01-01T00:00:00Z"}
