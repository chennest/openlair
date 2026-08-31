"""共享夹具：配置写到 tmp 目录，用 httpx.MockTransport 假扮后端，并走真实控制台入口拿退出码。"""

from __future__ import annotations

import io
import sys
from typing import Any, Callable
from unittest.mock import patch

import httpx
import pytest

from laircli import state
from laircli.app import main
from laircli.config import save
from samples import FAKE_KEY

Handler = Callable[[httpx.Request], httpx.Response]


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """每个用例独立的配置文件 + 干净的环境变量 + 干净的进程内缓存。"""
    monkeypatch.setenv("LAIRCLI_CONFIG", str(tmp_path / "config.toml"))
    for name in ("OPENLAIR_API_KEY", "OPENLAIR_BASE_URL", "OPENLAIR_BOOK_ID", "LAIRCLI_JSON"):
        monkeypatch.delenv(name, raising=False)
    state.reset()
    state._transport = None
    yield
    state.reset()
    state._transport = None


@pytest.fixture
def configured():
    """写好一把可用 Key。"""
    save({"api_key": FAKE_KEY, "base_url": "http://testserver", "user": "我"})
    return state.settings()


@pytest.fixture
def serve():
    """注入假后端。"""

    def _serve(handler: Handler) -> None:
        state._transport = httpx.MockTransport(handler)
        state.reset()

    return _serve


@pytest.fixture
def invoke():
    """经 `lair` 控制台入口跑一次，返回 (退出码, 合并输出)。"""

    def _invoke(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        real_out, real_err = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = buffer
        try:
            with patch.object(sys, "argv", ["lair", *argv]):
                main()
            code: Any = 0
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else 0
        except Exception as exc:  # 未翻译的异常：当成失败暴露出来，别让用例静默通过
            code = 70
            buffer.write(f"unhandled {type(exc).__name__}: {exc}\n")
        finally:
            sys.stdout, sys.stderr = real_out, real_err
        return code, buffer.getvalue()

    return _invoke
