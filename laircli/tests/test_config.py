"""配置落盘：文件内容、解析优先级、掩码。"""

from __future__ import annotations

import pytest

from laircli import config
from laircli.errors import CliError, NotConfigured


def test_save_then_load_round_trip():
    config.save({"api_key": "ol_abc", "base_url": "http://127.0.0.1:8001", "book_id": 12, "user": "我"})
    data = config.load()
    assert data == {"api_key": "ol_abc", "base_url": "http://127.0.0.1:8001", "book_id": 12, "user": "我"}


def test_awkward_values_do_not_break_the_file():
    """反斜杠与中文是 Windows 上最容易写坏的两类值。"""
    config.save({"base_url": "C:\\Users\\me\\proxy", "user": "我 · 小美"})
    data = config.load()
    assert data["base_url"] == "C:\\Users\\me\\proxy"
    assert data["user"] == "我 · 小美"


def test_unknown_keys_are_dropped():
    config.save({"api_key": "ol_abc", "evil": "x"})
    assert "evil" not in config.load()


def test_flag_beats_env_beats_file(monkeypatch):
    config.save({"api_key": "ol_from_file", "base_url": "http://file", "book_id": 1})
    assert config.resolve().api_key == "ol_from_file"

    monkeypatch.setenv("OPENLAIR_API_KEY", "ol_from_env")
    monkeypatch.setenv("OPENLAIR_BOOK_ID", "7")
    assert config.resolve().api_key == "ol_from_env"
    assert config.resolve().book_id == 7

    resolved = config.resolve(api_key="ol_from_flag", book_id=3)
    assert resolved.api_key == "ol_from_flag"
    assert resolved.book_id == 3
    assert resolved.base_url == "http://file"


def test_default_base_url_when_unconfigured(monkeypatch):
    monkeypatch.setenv("OPENLAIR_API_KEY", "ol_env_only")
    assert config.resolve().base_url == config.DEFAULT_BASE_URL


def test_missing_key_is_not_configured():
    with pytest.raises(NotConfigured) as exc:
        config.resolve()
    assert exc.value.exit_code == 3
    assert "lair init" in str(exc.value)


def test_non_numeric_book_id_reports_clearly(monkeypatch):
    monkeypatch.setenv("OPENLAIR_API_KEY", "ol_x")
    monkeypatch.setenv("OPENLAIR_BOOK_ID", "abc")
    with pytest.raises(CliError, match="OPENLAIR_BOOK_ID"):
        config.resolve()


def test_remove_last_key_deletes_file():
    config.save({"api_key": "ol_abc"})
    config.remove_keys("api_key")
    assert not config.config_path().exists()
    assert config.load() == {}


def test_mask_hides_most_of_the_key():
    key = "ol_" + "a" * 43
    assert config.mask(key) == key[:12] + "…"
    assert config.mask("short") == "***"


def test_broken_file_is_reported_not_swallowed():
    config.config_path().parent.mkdir(parents=True, exist_ok=True)
    config.config_path().write_text("= not toml =", encoding="utf-8")
    with pytest.raises(CliError, match="不可解析"):
        config.load()
