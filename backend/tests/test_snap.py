"""截图识别测试：端点契约（鉴权/格式/大小）+ JSON 提取纯函数。"""

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.snap import SnapParseData, _extract_json


def make_client(tmp_path, parser=None) -> TestClient:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-snap.db")
    if parser is not None:
        app.state.snap_parser = parser
    return TestClient(app)


class FakeParser:
    """假识别器：绕过真实 LLM 调用，验证端点链路与契约。"""

    async def parse(self, *, image_bytes: bytes, mime: str) -> dict:
        return {
            "type": "支出",
            "amount": 12.5,
            "category": "餐饮",
            "note": "午饭",
            "date": "2026-08-24",
            "confidence": 0.95,
        }


def login(client: TestClient) -> str:
    r = client.post("/api/auth/login", json={"email": "test1@openlair.dev", "password": "test123456"})
    assert r.status_code == 200
    return r.json()["data"]["token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- 端点 ----------


def test_parse_requires_auth(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.post("/api/snap/parse", files={"file": ("a.png", b"x", "image/png")})
    assert r.status_code == 401
    assert r.json()["code"] == 401


def test_reject_non_image(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    r = client.post(
        "/api/snap/parse", files={"file": ("a.txt", b"hello", "text/plain")}, headers=auth(token)
    )
    assert r.status_code == 400
    assert "仅支持" in r.json()["message"]


def test_reject_empty_file(tmp_path) -> None:
    client = make_client(tmp_path)
    token = login(client)
    r = client.post(
        "/api/snap/parse", files={"file": ("a.png", b"", "image/png")}, headers=auth(token)
    )
    assert r.status_code == 400


def test_parse_success_contract(tmp_path) -> None:
    client = make_client(tmp_path, parser=FakeParser())
    token = login(client)
    r = client.post(
        "/api/snap/parse",
        files={"file": ("a.png", b"\x89PNG fake bytes", "image/png")},
        headers=auth(token),
    )
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["amount"] == 12.5
    assert data["category"] == "餐饮"
    assert data["type"] == "支出"


# ---------- 纯函数 ----------


def test_extract_json_variants() -> None:
    assert _extract_json('```json\n{"a":1}\n```') == {"a": 1}
    assert _extract_json("好，识别结果如下：{\"a\":2} 就这些") == {"a": 2}
    assert _extract_json("no json here") is None


def test_snap_parse_data_defaults() -> None:
    d = SnapParseData.model_validate({"amount": 0})
    assert d.type == "支出"
    assert d.confidence == 0.0
    assert d.category == ""
