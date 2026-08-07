"""JWT 密钥解析优先级：进程环境 > OpenLair .env > 项目根 .env > 开发默认。"""

from pathlib import Path

from lairservice.core.security import DEV_SECRET, resolve_jwt_secret


def test_resolve_jwt_secret_priority_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENLAIR_JWT_SECRET", "env-secret-key-1234567890abcdef")
    assert resolve_jwt_secret() == "env-secret-key-1234567890abcdef"


def test_resolve_jwt_secret_falls_back_through_chain(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("OPENLAIR_JWT_SECRET", raising=False)
    secret = resolve_jwt_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 32  # 无论走项目 .env 还是 DEV_SECRET，都满足 HS256 最小密钥长度
    assert secret == DEV_SECRET or Path(__file__).resolve().parents[1].joinpath(".env").exists()


def test_env_example_has_jwt_secret_key() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    assert example.exists()
    content = example.read_text(encoding="utf-8")
    assert "OPENLAIR_JWT_SECRET" in content