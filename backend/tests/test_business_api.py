"""业务 API 全链路测试：统一信封 + JWT 鉴权 + 各模块契约（与前端 mock 契约对齐）。"""

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path) -> TestClient:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-biz.db")
    # 测试环境开放注册（生产默认禁止，由 settings.allow_register 控制，见 test_register_closed_by_default）
    app.state.setting_repo.set("allow_register", "1")
    return TestClient(app)


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


def test_register_closed_by_default(tmp_path) -> None:
    """生产默认禁止注册（settings.allow_register 缺省 "0"），开放需显式置 "1"。"""
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-closed.db")
    client = TestClient(app)
    r = client.post(
        "/api/auth/register",
        json={"name": "路人", "email": "walkin@openlair.dev", "password": "abc12345"},
    )
    assert r.status_code == 403
    assert r.json()["code"] == 403
    assert r.json()["data"] is None


def test_register_status_endpoint(tmp_path) -> None:
    """注册开关查询：默认关闭 false，显式置 "1" 后 true（供前端动态渲染注册入口）。"""
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-status.db")
    client = TestClient(app)
    r = client.get("/api/auth/register-status")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200
    assert body["data"] == {"allowRegister": False}

    app.state.setting_repo.set("allow_register", "1")
    r = client.get("/api/auth/register-status")
    assert r.json()["data"] == {"allowRegister": True}


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
    for path in ("/api/ledger", "/api/books", "/api/todo", "/api/calendar", "/api/notes", "/api/habits", "/api/days", "/api/overview"):
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
    assert len(cats) == 26  # 系统预置 18 支出 + 8 收入
    assert cats[0]["id"] == 1
    assert cats[0]["name"] == "餐饮"
    # 全局 sort_order：支出块在前（其他兜底位 17），收入块从 18 起
    assert cats[17]["name"] == "其他" and cats[17]["type"] == "支出"
    assert cats[18]["type"] == "收入"
    # 系统预置 userId 为空
    assert all(c["userId"] is None for c in cats)


def test_category_crud_and_visibility(tmp_path) -> None:
    client = make_client(tmp_path)
    token, _ = login(client)
    h = auth_headers(token)

    # 创建 → userId 归属当前用户、排同类型末尾
    r = client.post("/api/ledger/categories", headers=h, json={"name": "手办", "type": "支出"})
    assert r.status_code == 200
    cat = r.json()["data"]
    assert cat["userId"] == 1 and cat["type"] == "支出"

    # 与系统预置重名 → 409
    r = client.post("/api/ledger/categories", headers=h, json={"name": "餐饮", "type": "支出"})
    assert r.status_code == 409

    # 再次同名 → 409
    r = client.post("/api/ledger/categories", headers=h, json={"name": "手办", "type": "支出"})
    assert r.status_code == 409

    # 不带 bookId 可见本人自定义；bookId=2（本人是 owner）同样可见
    cats = client.get("/api/ledger/categories", headers=h).json()["data"]
    assert any(c["id"] == cat["id"] for c in cats)
    cats_book2 = client.get("/api/ledger/categories?bookId=2", headers=h).json()["data"]
    assert any(c["id"] == cat["id"] for c in cats_book2)

    # 改名
    r = client.put(f"/api/ledger/categories/{cat['id']}", headers=h, json={"name": "数码硬件"})
    assert r.json()["data"]["name"] == "数码硬件"

    # 系统预置不可改/删
    r = client.put("/api/ledger/categories/1", headers=h, json={"name": "改餐饮"})
    assert r.status_code == 403
    r = client.delete("/api/ledger/categories/1", headers=h)
    assert r.status_code == 403

    # 删除保护：先把一条流水挂到该分类再删 → 409
    r = client.post(
        "/api/ledger",
        headers=h,
        json={"type": "支出", "categoryId": cat["id"], "amount": 9.9, "note": "删测专用", "bookId": 1},
    )
    assert r.status_code == 200
    r = client.delete(f"/api/ledger/categories/{cat['id']}", headers=h)
    assert r.status_code == 409

    # 删掉流水后可正常删除
    listed = client.get("/api/ledger?bookId=1&keyword=删测专用", headers=h).json()["data"]
    assert listed["total"] >= 1
    tx_id = listed["transactions"][0]["id"]
    client.delete(f"/api/ledger/{tx_id}", headers=h)
    r = client.delete(f"/api/ledger/categories/{cat['id']}", headers=h)
    assert r.status_code == 200
    # 回归钉死：删除返回 200 后分类必须真的消失（曾出现校验通过但不执行删除的 bug）
    cats_after = client.get("/api/ledger/categories", headers=h).json()["data"]
    assert all(c["id"] != cat["id"] for c in cats_after)


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
    headers = auth_headers(token)
    r = client.get("/api/overview", headers=headers)
    data = r.json()["data"]
    assert set(data) == {"monthExpense", "recentLedger", "todos", "upcoming", "habits"}
    assert data["monthExpense"]["amount"] >= 0
    assert data["monthExpense"]["budget"] > 0
    assert len(data["todos"]) <= 4
    assert len(data["upcoming"]) <= 3
    assert isinstance(data["recentLedger"], list)
    assert len(data["recentLedger"]) <= 10

    # 记两笔后，recentLedger 按日期+id 倒序返回，新记的两笔排最前（含分类名）
    client.post(
        "/api/ledger",
        json={"type": "支出", "categoryId": 1, "amount": 38.5, "note": "午饭", "bookId": 1},
        headers=headers,
    )
    client.post(
        "/api/ledger",
        json={"type": "收入", "categoryId": 2, "amount": 12000, "note": "工资", "bookId": 1},
        headers=headers,
    )
    data = client.get("/api/overview", headers=headers).json()["data"]
    assert [t["note"] for t in data["recentLedger"][:2]] == ["工资", "午饭"]
    assert data["recentLedger"][1]["amount"] == 38.5
    assert data["recentLedger"][1]["type"] == "支出"
    assert data["recentLedger"][1]["category"]

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

def test_book_invite_code_generate_reset_disable(tmp_path) -> None:
    """邀请码：转共享自动生成、owner 查看/重置/关闭、非 owner 拒绝。"""
    client = make_client(tmp_path)
    token, _ = login(client)  # test1 = owner
    headers = auth_headers(token)

    # 新建个人账本 → 转为共享：自动生成邀请码
    r = client.post("/api/books", json={"name": "出游账", "type": "personal"}, headers=headers)
    book_id = r.json()["data"]["book"]["id"]
    client.post(f"/api/books/{book_id}/convert", headers=headers)
    code = client.get(f"/api/books/{book_id}/invite", headers=headers).json()["data"]["code"]
    assert isinstance(code, str) and len(code) == 8

    # seed 共享账本 2 未生成码 → GET 返回 null
    assert client.get("/api/books/2/invite", headers=headers).json()["data"]["code"] is None

    # 生成码（seed 共享账本 2）
    r = client.post("/api/books/2/invite", headers=headers)
    assert r.json()["code"] == 200
    code2 = r.json()["data"]["code"]
    assert len(code2) == 8
    assert client.get("/api/books/2/invite", headers=headers).json()["data"]["code"] == code2

    # 非 owner 不能看码/重置码
    token2, _ = login(client, email="test2@openlair.dev")
    h2 = auth_headers(token2)
    assert client.get("/api/books/2/invite", headers=h2).status_code == 403
    assert client.post("/api/books/2/invite", headers=h2).status_code == 403
    assert client.delete("/api/books/2/invite", headers=h2).status_code == 403

    # 个人账本不能生成码
    r = client.post("/api/books/1/invite", headers=headers)
    assert r.status_code == 400

    # 重置：新码 != 旧码
    r = client.post("/api/books/2/invite", headers=headers)
    code2b = r.json()["data"]["code"]
    assert code2b != code2

    # 关闭邀请：置空码
    assert client.delete("/api/books/2/invite", headers=headers).json()["data"]["ok"] is True
    assert client.get("/api/books/2/invite", headers=headers).json()["data"]["code"] is None


def test_book_join_and_leave(tmp_path) -> None:
    """邀请码加入：成功加入、旧码失效、已在账本 409、无效码 404、退出。"""
    client = make_client(tmp_path)
    token, _ = login(client)  # test1 = owner
    headers = auth_headers(token)

    # owner 为 seed 共享账本 2 生成码
    code = client.post("/api/books/2/invite", headers=headers).json()["data"]["code"]

    # 注册一个全新用户 joiner 并登录
    client.post("/api/auth/register", json={"name": "join", "email": "joiner@test.dev", "password": "test123456"})
    jt, ju = login(client, email="joiner@test.dev")

    # 加入成功（码带连字符 + 小写也应被识别）
    r = client.post("/api/books/join", json={"code": f"{code[:4]}-{code[4:].lower()}"}, headers=auth_headers(jt))
    assert r.status_code == 200
    book = r.json()["data"]["book"]
    assert book["id"] == 2
    assert any(m["userId"] == ju["id"] and m["role"] == "editor" for m in book["members"])

    # 已在账本中 → 409
    r = client.post("/api/books/join", json={"code": code}, headers=auth_headers(jt))
    assert r.status_code == 409

    # 无效码 → 404
    r = client.post("/api/books/join", json={"code": "ZZZZZZZZ"}, headers=auth_headers(jt))
    assert r.status_code == 404

    # 重置后旧码失效：新用户用旧码加入 → 404
    code_new = client.post("/api/books/2/invite", headers=headers).json()["data"]["code"]
    client.post("/api/auth/register", json={"name": "join2", "email": "joiner2@test.dev", "password": "test123456"})
    j2t, _ = login(client, email="joiner2@test.dev")
    assert client.post("/api/books/join", json={"code": code}, headers=auth_headers(j2t)).status_code == 404
    assert client.post("/api/books/join", json={"code": code_new}, headers=auth_headers(j2t)).status_code == 200

    # 成员自助退出：editor 可退，owner 不可退
    r = client.post("/api/books/2/leave", headers=auth_headers(jt))
    assert r.json()["data"]["ok"] is True
    r = client.post("/api/books/2/leave", headers=headers)
    assert r.status_code == 400
    # 退出后不再是成员，再退 → 404
    assert client.post("/api/books/2/leave", headers=auth_headers(jt)).status_code == 404


def test_book_convert_to_shared_one_way(tmp_path) -> None:
    """个人账本 → 共享（单向）：转成功、已是共享拒绝、共享不可转回、非 owner 拒绝。"""
    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)

    # 新建个人账本
    r = client.post("/api/books", json={"name": "私人账", "type": "personal"}, headers=headers)
    book = r.json()["data"]["book"]
    assert book["type"] == "personal"

    # 转为共享
    r = client.post(f"/api/books/{book['id']}/convert", headers=headers)
    assert r.json()["data"]["book"]["type"] == "shared"

    # 已是共享 → 400
    r = client.post(f"/api/books/{book['id']}/convert", headers=headers)
    assert r.status_code == 400

    # 没有转回个人的接口：type 保持 shared
    books = client.get("/api/books", headers=headers).json()["data"]
    assert next(b for b in books if b["id"] == book["id"])["type"] == "shared"

    # 非 owner 不能转换（test2 不是该账本成员/owner）
    token2, _ = login(client, email="test2@openlair.dev")
    h2 = auth_headers(token2)
    assert client.post(f"/api/books/{book['id']}/convert", headers=h2).status_code == 403


# ---------- days（倒数日 / 纪念日） ----------

def test_days_crud_and_countdown(tmp_path) -> None:
    """全链路：创建四种状态的日子 → 排序 → 更新 → 删除，DTO 契约与前端对齐。"""
    import datetime as _dt

    client = make_client(tmp_path)
    # 注册全新用户：seed 演示日子都挂在 user 1 名下，新用户列表从零开始，断言不受干扰
    client.post("/api/auth/register", json={"name": "日子用户", "email": "days@openlair.dev", "password": "test123456"})
    token, _ = login(client, email="days@openlair.dev")
    headers = auth_headers(token)
    today = _dt.date.today()

    # 一次性倒数：3 天后
    r = client.post(
        "/api/days",
        json={"title": "考研初试", "date": str(today + _dt.timedelta(days=3)), "emoji": "📚"},
        headers=headers,
    )
    assert r.json()["code"] == 200
    item = r.json()["data"]["item"]
    assert item["daysUntil"] == 3
    assert item["repeat"] == "once"
    assert item["milestone"] is None

    # 今天 → daysUntil 0
    r = client.post("/api/days", json={"title": "项目上线", "date": str(today)}, headers=headers)
    assert r.json()["data"]["item"]["daysUntil"] == 0

    # 每年生日：2 年前的「今天+12 天」→ 还有 12 天、第 3 次
    birthday = (today + _dt.timedelta(days=12)).replace(year=today.year - 2)
    r = client.post(
        "/api/days",
        json={"title": "宝宝生日", "date": birthday.isoformat(), "repeat": "yearly", "pinned": True},
        headers=headers,
    )
    yearly_id = r.json()["data"]["id"]
    item = r.json()["data"]["item"]
    assert item["daysUntil"] == 12
    assert item["milestone"] == 3

    # 一次性过去：400 天前 → 累计 -400
    r = client.post(
        "/api/days",
        json={"title": "在一起", "date": str(today - _dt.timedelta(days=400))},
        headers=headers,
    )
    assert r.json()["data"]["item"]["daysUntil"] == -400

    # 列表：置顶在前，其余按 |daysUntil| 升序；DTO 字段齐全
    days = client.get("/api/days", headers=headers).json()["data"]["days"]
    assert [d["title"] for d in days] == ["宝宝生日", "项目上线", "考研初试", "在一起"]
    assert set(days[0]) == {
        "id", "title", "emoji", "date", "repeat", "pinned", "daysUntil", "milestone", "createdAt", "updatedAt",
    }

    # 更新：改标题 + 取消置顶
    r = client.put(f"/api/days/{yearly_id}", json={"title": "儿子生日", "pinned": False}, headers=headers)
    assert r.json()["data"]["item"]["title"] == "儿子生日"
    assert r.json()["data"]["item"]["pinned"] is False

    # 删除后更新 → 404
    r = client.delete(f"/api/days/{yearly_id}", headers=headers)
    assert r.json()["data"] == {"ok": True}
    r = client.put(f"/api/days/{yearly_id}", json={"title": "x"}, headers=headers)
    assert r.json()["code"] == 404

    # 非法 repeat 归一为 once；标题纯空白兜底
    r = client.post(
        "/api/days",
        json={"title": "  ", "date": str(today + _dt.timedelta(days=1)), "repeat": "weekly"},
        headers=headers,
    )
    item = r.json()["data"]["item"]
    assert item["repeat"] == "once"
    assert item["title"] == "未命名日子"


def test_days_monthly_and_feb29(tmp_path) -> None:
    """monthly 月末截断 + yearly 2/29 平年落 2/28：不崩且下一次不早于今天。"""
    import calendar as _calendar
    import datetime as _dt

    client = make_client(tmp_path)
    token, _ = login(client)
    headers = auth_headers(token)
    today = _dt.date.today()

    # monthly：上月 15 号 → 下一次 = 本月/下月 15 号（与后端同规则独立复算）
    prev_month_15 = (today.replace(day=1) - _dt.timedelta(days=1)).replace(day=15)
    r = client.post(
        "/api/days",
        json={"title": "发工资", "date": prev_month_15.isoformat(), "repeat": "monthly"},
        headers=headers,
    )
    item = r.json()["data"]["item"]

    def month_day(day: int, year: int, month: int) -> _dt.date:
        return _dt.date(year, month, min(day, _calendar.monthrange(year, month)[1]))

    y, m = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
    expected = month_day(15, today.year, today.month)
    if expected < today:
        expected = month_day(15, y, m)
    assert item["daysUntil"] == (expected - today).days

    # yearly：2004-02-29（2/29 出生）→ 平年落 2/28，正常返回非负倒数
    r = client.post(
        "/api/days",
        json={"title": "闰日生日", "date": "2004-02-29", "repeat": "yearly"},
        headers=headers,
    )
    assert r.json()["code"] == 200
    item = r.json()["data"]["item"]
    assert item["daysUntil"] >= 0
    assert item["milestone"] is not None and item["milestone"] >= 1
