"""JWT 密钥解析：环境变量 OPENLAIR_JWT_SECRET > 项目 .env > 开发默认（pydantic-settings 处理）。"""

from pathlib import Path

from lairservice.core.security import resolve_jwt_secret


def test_resolve_jwt_secret_priority_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENLAIR_JWT_SECRET", "env-secret-key-1234567890abcdef")
    assert resolve_jwt_secret() == "env-secret-key-1234567890abcdef"


def test_resolve_jwt_secret_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.delenv("OPENLAIR_JWT_SECRET", raising=False)
    secret = resolve_jwt_secret()
    assert isinstance(secret, str)
    assert len(secret) >= 32  # 无论走项目 .env 还是默认值，都满足 HS256 最小密钥长度


def test_env_example_has_jwt_secret_key() -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    assert example.exists()
    content = example.read_text(encoding="utf-8")
    assert "OPENLAIR_JWT_SECRET" in content
    assert "DATABASE_URL" in content