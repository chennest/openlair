"""API Key 全链路测试：创建 / X-API-Key 鉴权访问 / 列表不回显明文 / 撤销立即失效。"""

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-keys.db"))


def login(client: TestClient, email: str = "test1@openlair.dev") -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": "test123456"})
    assert response.status_code == 200
    return response.json()["data"]["token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def api_key_headers(api_key: str) -> dict:
    return {"X-API-Key": api_key}


# ---------- 未鉴权 ----------

def test_keys_endpoints_require_token(tmp_path) -> None:
    client = make_client(tmp_path)
    for method, path in (("get", "/api/keys"), ("post", "/api/keys"), ("delete", "/api/keys/1")):
        r = getattr(client, method)(path)
        assert r.status_code == 401, (method, path)
        assert r.json()["code"] == 401


# ---------- 创建 ----------

def test_create_key_returns_plaintext_once(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    r = client.post("/api/keys", json={"name": "我的 MCP"}, headers=auth_headers(token))
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["apiKey"].startswith("ol_")
    assert data["item"]["name"] == "我的 MCP"
    assert data["item"]["prefix"] == data["apiKey"][:12]
    assert "keyHash" not in data["item"]


def test_create_key_invalid_name(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    # Pydantic 层拦截：空/超长 → 422
    for name in ("", "x" * 31):
        r = client.post("/api/keys", json={"name": name}, headers=auth_headers(token))
        assert r.status_code == 422, name
    # 服务层拦截：纯空格可过 Pydantic（长度 1），strip 后为空 → 400
    r = client.post("/api/keys", json={"name": "   "}, headers=auth_headers(token))
    assert r.status_code == 400


# ---------- 用 Key 访问接口 ----------

def test_api_key_can_access_business_endpoints(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    api_key = client.post("/api/keys", json={"name": "test"}, headers=auth_headers(token)).json()["data"]["apiKey"]

    # /api/auth/me（用户身份）
    r = client.get("/api/auth/me", headers=api_key_headers(api_key))
    assert r.status_code == 200
    assert r.json()["data"]["id"] == 1

    # 业务接口
    for path in ("/api/todo", "/api/habits", "/api/overview"):
        r = client.get(path, headers=api_key_headers(api_key))
        assert r.status_code == 200, path


def test_api_key_updates_last_used(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    api_key_data = client.post("/api/keys", json={"name": "test"}, headers=auth_headers(token)).json()["data"]
    client.get("/api/auth/me", headers=api_key_headers(api_key_data["apiKey"]))
    keys = client.get("/api/keys", headers=auth_headers(token)).json()["data"]["keys"]
    target = next(k for k in keys if k["id"] == api_key_data["item"]["id"])
    assert target["lastUsedAt"] is not None


def test_invalid_api_key_401(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.get("/api/auth/me", headers=api_key_headers("ol_invalid_key_xxx"))
    assert r.status_code == 401


# ---------- 列表 / 撤销 ----------

def test_list_never_exposes_plaintext_or_hash(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    client.post("/api/keys", json={"name": "a"}, headers=auth_headers(token))
    client.post("/api/keys", json={"name": "b"}, headers=auth_headers(token))
    keys = client.get("/api/keys", headers=auth_headers(token)).json()["data"]["keys"]
    assert len(keys) == 2
    for k in keys:
        assert "apiKey" not in k
        assert "keyHash" not in k
        assert k["name"] in ("a", "b")


def test_revoke_key_invalidates_immediately(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    data = client.post("/api/keys", json={"name": "临时"}, headers=auth_headers(token)).json()["data"]

    r = client.delete(f"/api/keys/{data['item']['id']}", headers=auth_headers(token))
    assert r.status_code == 200

    # 撤销后 Key 立即失效
    r = client.get("/api/auth/me", headers=api_key_headers(data["apiKey"]))
    assert r.status_code == 401
    # 列表不再包含
    keys = client.get("/api/keys", headers=auth_headers(token)).json()["data"]["keys"]
    assert keys == []


def test_cannot_revoke_others_key(tmp_path) -> None:
    client = make_client(tmp_path)
    token1 = login(client, "test1@openlair.dev")
    token2 = login(client, "test2@openlair.dev")
    data = client.post("/api/keys", json={"name": "t1"}, headers=auth_headers(token1)).json()["data"]
    r = client.delete(f"/api/keys/{data['item']['id']}", headers=auth_headers(token2))
    assert r.status_code == 404
