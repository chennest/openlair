"""系统路由测试：/healthz 探针 + /metrics（K8s 探针与 Prometheus 指标）。"""

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path) -> TestClient:
    return TestClient(create_app(database_url=f"sqlite+pysqlite:///{tmp_path}/lair-system.db"))


def test_liveness_ok(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.get("/healthz/live")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readiness_ok(tmp_path) -> None:
    client = make_client(tmp_path)
    r = client.get("/healthz/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_readiness_db_down_503(tmp_path, monkeypatch) -> None:
    client = make_client(tmp_path)

    class _BrokenSessionFactory:
        def __call__(self):
            raise ConnectionError("database connection refused")

    monkeypatch.setattr(client.app.state, "session_factory", _BrokenSessionFactory())
    r = client.get("/healthz/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "unavailable"
    assert "connection refused" in body["detail"]


def test_old_health_removed(tmp_path) -> None:
    client = make_client(tmp_path)
    assert client.get("/health").status_code == 404


def test_metrics_exposition(tmp_path) -> None:
    client = make_client(tmp_path)
    # 制造 HTTP 请求产生指标（无 token 访问业务路由 → 401）
    client.get("/api/auth/me")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    assert "http_requests_total" in r.text
    # 探针自身路径不应计入指标
    assert "healthz" not in r.text
