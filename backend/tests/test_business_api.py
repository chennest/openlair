"""业务 API 全链路测试：统一信封 + JWT 鉴权 + 各模块契约（与前端 mock 契约对齐）。"""

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-biz.db"))


def login(client: TestClient, email: str = "test1@openlair.dev") -> tuple[str, dict]:
    response = client.post(
        "/api/auth/login", json={"email": email, "password": "test123456"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    return body["data"]["token"], body["data"]["user"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- auth ----------

def test_seed_accounts_can_login(tmp_path) -> None:
    client = make_client(tmp_path)
    for i in (1, 2, 3):
        token, user = login(client, f"test{i}@openlair.dev")
        assert user["id"] == i
        assert user["email"] == f"test{i}@openlair.dev"
        assert "passwordHash" not in user
        assert len(token.split(".")) == 3


def test_register_then_login(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.post(
        "/api/auth/register",
        json={"name": "新用户", "email": "new@openlair.dev", "password": "abc12345"},
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["user"]["email"] == "new@openlair.dev"
    assert data["user"]["id"] == 4  # 自增

    r = client.post("/api/auth/login", json={"email": "new@openlair.dev", "password": "abc12345"})
    assert r.status_code == 200
    assert r.json()["code"] == 200


def test_register_duplicate_email_409(tmp_path) -> None:
    client = make_client(tmp_path)
    payload = {"name": "重复", "email": "test1@openlair.dev", "password": "abc12345"}
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409
    assert r.json()["code"] == 409
    assert r.json()["data"] is None


def test_login_wrong_password_401(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.post("/api/auth/login", json={"email": "test1@openlair.dev", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["message"] == "邮箱或密码错误"


def test_me_returns_current_user(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.get("/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["data"]["id"] == 1


def test_logout_revokes_token(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.post("/api/auth/logout", headers=auth_headers(token))
    assert r.json()["code"] == 200
    # 同 token 立即失效
    r = client.get("/api/auth/me", headers=auth_headers(token))
    assert r.status_code == 401


# ---------- 鉴权 ----------

def test_business_endpoints_require_token(tmp_path) -> None:
    client = make_client(tmp_path)
    for path in ("/api/ledger", "/api/books", "/api/todo", "/api/calendar", "/api/notes", "/api/habits", "/api/overview"):
        r = client.get(path)
        assert r.status_code == 401, path
        assert r.json()["code"] == 401
        assert r.json()["data"] is None


def test_invalid_token_401(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.get("/api/ledger", headers=auth_headers("abc.def.ghi"))
    assert r.status_code == 401


# ---------- ledger ----------

def test_ledger_categories(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.get("/api/ledger/categories", headers=auth_headers(token))
    cats = r.json()["data"]
    assert len(cats) == 16
    assert cats[0]["id"] == 1
    assert cats[0]["name"] == "餐饮"
    assert cats[10]["type"] == "收入"


def test_ledger_list_seed_data_by_book(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.get("/api/ledger?bookId=1&pageSize=5", headers=auth_headers(token))
    body = r.json()
    assert body["code"] == 200
    data = body["data"]
    assert data["total"] == 85  # seed：个人账本 85 条
    assert len(data["transactions"]) == 5
    tx = data["transactions"][0]
    assert set(tx) >= {"id", "type", "categoryId", "category", "bookId", "userId", "userName", "amount", "date", "note"}
    assert tx["date"]  # YYYY-MM-DD
    assert data["summary"]["expense"] > 0
    assert data["categoryStats"]
    assert data["budget"] == 5000

    r2 = client.get("/api/ledger?bookId=2", headers=auth_headers(token))
    assert r2.json()["data"]["total"] == 15  # 共享账本 15 条


def test_ledger_filter_and_pagination(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.get("/api/ledger?bookId=1&type=支出&keyword=午饭&page=2&pageSize=10", headers=auth_headers(token))
    body = r.json()["data"]
    assert body["page"] == 2
    assert len(body["transactions"]) <= 10
    for tx in body["transactions"]:
        assert tx["type"] == "支出"


def test_ledger_create_update_remove(tmp_path) -> None:
    client = make_client(tmp_path)
    token, user = login(client)
    headers = auth_headers(token)

    r = client.post(
        "/api/ledger",
        json={"type": "支出", "categoryId": 1, "amount": 36.5, "date": "2026-08-07", "note": "测试流水", "bookId": 1},
        headers=headers,
    )
    assert r.json()["code"] == 200
    item = r.json()["data"]["item"]
    assert item["userId"] == user["id"]  # 记账人 = 当前登录用户
    assert item["category"] == "餐饮"
    tx_id = item["id"]

    r = client.put(
        f"/api/ledger/{tx_id}", json={"note": "改过的备注"}, headers=headers
    )
    assert r.json()["data"]["item"]["note"] == "改过的备注"

    r = client.delete(f"/api/ledger/{tx_id}", headers=headers)
    assert r.json()["data"] == {"ok": True}

    r = client.delete(f"/api/ledger/{tx_id}", headers=headers)
    assert r.status_code == 404


def test_ledger_trend_and_budget(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    trend = client.get("/api/ledger/trend?bookId=1", headers=headers).json()["data"]
    assert len(trend) == 6
    assert set(trend[0]) == {"month", "income", "expense"}

    r = client.put("/api/ledger/budget", json={"bookId": 1, "amount": 8888}, headers=headers)
    assert r.json()["data"]["budget"] == 8888
    r = client.get("/api/ledger/budget?bookId=1", headers=headers)
    assert r.json()["data"]["budget"] == 8888


# ---------- books ----------

def test_books_list_create_members(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    books = client.get("/api/books", headers=headers).json()["data"]
    assert len(books) == 2
    assert books[0]["id"] == 1
    assert books[0]["type"] == "personal"
    shared = books[1]
    assert shared["type"] == "shared"
    assert len(shared["members"]) == 3
    assert shared["members"][0]["user"]["name"] == "我"
    assert shared["members"][0]["role"] == "owner"

    # 建账本：当前用户为 owner
    r = client.post("/api/books", json={"name": "大理旅行", "type": "shared"}, headers=headers)
    book = r.json()["data"]["book"]
    assert book["id"] == 3
    assert book["members"][0]["role"] == "owner"
    assert book["members"][0]["userId"] == 1

    # 按 id 添加已有用户
    r = client.post(f"/api/books/{book['id']}/members", json={"userId": 2}, headers=headers)
    assert len(r.json()["data"]["book"]["members"]) == 2

    # 重复添加 409
    r = client.post(f"/api/books/{book['id']}/members", json={"userId": 2}, headers=headers)
    assert r.status_code == 409

    # 按名字新建用户
    r = client.post(f"/api/books/{book['id']}/members", json={"name": "小红"}, headers=headers)
    member_user = r.json()["data"]["book"]["members"][-1]["user"]
    assert member_user["name"] == "小红"

    # owner 不可移除
    r = client.delete(f"/api/books/{book['id']}/members/1", headers=headers)
    assert r.status_code == 400

    # 移除 editor
    r = client.delete(f"/api/books/{book['id']}/members/2", headers=headers)
    assert r.status_code == 200


# ---------- 其余模块 CRUD ----------

def test_todo_crud(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    items = client.get("/api/todo", headers=headers).json()["data"]["todos"]
    assert len(items) == 8  # seed

    r = client.post("/api/todo", json={"text": "新待办", "quadrant": "重要紧急", "due": "今天"}, headers=headers)
    todo_id = r.json()["data"]["id"]
    r = client.put(f"/api/todo/{todo_id}", json={"done": True}, headers=headers)
    assert r.json()["data"]["item"]["done"] is True
    r = client.delete(f"/api/todo/{todo_id}", headers=headers)
    assert r.json()["data"] == {"ok": True}


def test_calendar_notes_habits_crud(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    # calendar
    r = client.post("/api/calendar", json={"title": "开会", "date": "2026-08-10", "time": "14:00"}, headers=headers)
    event_id = r.json()["data"]["id"]
    created = r.json()["data"]["item"]
    assert created["title"] == "开会"
    assert any(e["title"] == "开会" for e in client.get("/api/calendar", headers=headers).json()["data"]["events"])
    client.delete(f"/api/calendar/{event_id}", headers=headers)

    # notes
    r = client.post("/api/notes", json={"title": "新笔记", "summary": "摘要", "tags": ["工作"]}, headers=headers)
    note_id = r.json()["data"]["id"]
    note = client.get("/api/notes", headers=headers).json()["data"]["notes"][0]
    assert note["tags"] == ["工作"]
    client.delete(f"/api/notes/{note_id}", headers=headers)

    # habits
    r = client.post("/api/habits", json={"name": "喝水"}, headers=headers)
    habit_id = r.json()["data"]["id"]
    r = client.put(f"/api/habits/{habit_id}", json={"done": True}, headers=headers)
    assert r.json()["data"]["item"]["done"] is True
    client.delete(f"/api/habits/{habit_id}", headers=headers)


def test_overview_aggregates(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    r = client.get("/api/overview", headers=auth_headers(token))
    data = r.json()["data"]
    assert set(data) == {"monthExpense", "todos", "upcoming", "habits"}
    assert data["monthExpense"]["amount"] >= 0
    assert data["monthExpense"]["budget"] > 0
    assert len(data["todos"]) <= 4
    assert len(data["upcoming"]) <= 3

def test_books_trash_restore_purge(tmp_path) -> None:
    """回收站流程：软删 → 列表消失 → trash 可见 → 恢复 → 彻底删除级联清数据。"""
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    # 建一个账本并加成员/流水
    r = client.post("/api/books", json={"name": "待删除账本", "type": "shared"}, headers=headers)
    book_id = r.json()["data"]["book"]["id"]
    client.post(f"/api/books/{book_id}/members", json={"userId": 2}, headers=headers)
    r = client.post("/api/ledger", json={"type": "支出", "categoryId": 1, "amount": 100, "bookId": book_id}, headers=headers)
    assert r.status_code == 200

    # 软删：owner 成功，列表消失
    r = client.delete(f"/api/books/{book_id}", headers=headers)
    assert r.json()["data"]["ok"] is True
    ids = [b["id"] for b in client.get("/api/books", headers=headers).json()["data"]]
    assert book_id not in ids

    # 回收站可见（含成员信息）
    trash = client.get("/api/books/trash", headers=headers).json()["data"]
    assert any(b["id"] == book_id for b in trash)
    deleted = next(b for b in trash if b["id"] == book_id)
    assert len(deleted["members"]) == 2  # owner + 成员仍在

    # 非 owner 不能操作（用 test2 登录）
    token2, _ = login(client, email="test2@openlair.dev")
    headers2 = auth_headers(token2)
    assert client.delete(f"/api/books/{book_id}", headers=headers2).status_code == 403
    assert client.post(f"/api/books/{book_id}/restore", headers=headers2).status_code == 403
    assert client.delete(f"/api/books/{book_id}/purge", headers=headers2).status_code == 403

    # 恢复：回到正常列表
    r = client.post(f"/api/books/{book_id}/restore", headers=headers)
    assert r.json()["data"]["ok"] is True
    ids = [b["id"] for b in client.get("/api/books", headers=headers).json()["data"]]
    assert book_id in ids
    assert all(b["id"] != book_id for b in client.get("/api/books/trash", headers=headers).json()["data"])

    # 再软删 → 彻底删除：级联清流水/成员
    client.delete(f"/api/books/{book_id}", headers=headers)
    r = client.delete(f"/api/books/{book_id}/purge", headers=headers)
    assert r.json()["data"]["ok"] is True
    assert all(b["id"] != book_id for b in client.get("/api/books/trash", headers=headers).json()["data"])
    # 账本已彻底删除：查询该账本流水 → 404（原流水随账本级联删除，不可再访问）
    r = client.get(f"/api/ledger?bookId={book_id}&pageSize=1", headers=headers)
    assert r.status_code == 404

def test_ledger_create_requires_existing_book(tmp_path) -> None:
    """账本不存在/已删除时禁止入账（修复 fallback 到默认账本的隐患）。"""
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    # 不传 bookId → 400
    r = client.post("/api/ledger", json={"type": "支出", "categoryId": 1, "amount": 10}, headers=headers)
    assert r.status_code == 400

    # 不存在的账本 → 404
    r = client.post(
        "/api/ledger", json={"type": "支出", "categoryId": 1, "amount": 10, "bookId": 999}, headers=headers
    )
    assert r.status_code == 404

    # 软删除的账本 → 404
    client.delete("/api/books/2", headers=headers)
    r = client.post(
        "/api/ledger", json={"type": "支出", "categoryId": 1, "amount": 10, "bookId": 2}, headers=headers
    )
    assert r.status_code == 404

def test_books_list_isolated_per_user(tmp_path) -> None:
    """多用户隔离：只返回当前用户是成员的账本。"""
    client = make_client(tmp_path)
    token1, _ = login(client)
    h1 = auth_headers(token1)

    # test1（seed 账本 1/2 的成员）
    ids1 = [b["id"] for b in client.get("/api/books", headers=h1).json()["data"]]
    assert sorted(ids1) == [1, 2]

    # test4（新注册，非任何账本成员）→ 空列表
    r = client.post("/api/auth/register", json={"name": "t4", "email": "t4@test.dev", "password": "test123456"})
    token4 = r.json()["data"]["token"]
    h4 = auth_headers(token4)
    assert client.get("/api/books", headers=h4).json()["data"] == []

    # test4 建账本后只能看到自己的
    r = client.post("/api/books", json={"name": "我的私人账本", "type": "personal"}, headers=h4)
    my_book = r.json()["data"]["book"]["id"]
    ids4 = [b["id"] for b in client.get("/api/books", headers=h4).json()["data"]]
    assert ids4 == [my_book]
    # test1 看不到 test4 的账本
    ids1 = [b["id"] for b in client.get("/api/books", headers=h1).json()["data"]]
    assert my_book not in ids1
    # test4 不是 test1 账本的 owner，不能删除
    assert client.delete("/api/books/1", headers=h4).status_code == 403
