from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import os


DEFAULT_OPENLAIR_CONFIG_PATH = Path.home() / ".openlair" / "openlair.json"

DEFAULT_OPENLAIR_CONFIG_TEMPLATE: dict[str, Any] = {
    "model": {
        "default_route": "agent",
        "routes": {
            "agent": "main",
            "chat": "main",
            "summary": "main",
        },
        "providers": {
            "main": {
                "kind": "openai_compatible",
                "model": "replace-with-model-name",
                "base_url": "https://replace-with-provider-base-url/v1",
                "api_key_env": "OPENLAIR_MODEL_API_KEY",
                "timeout_seconds": 60,
            }
        },
    }
}


@dataclass(frozen=True)
class OpenLairConfig:
    path: Path
    data: dict[str, Any]

    @property
    def model(self) -> dict[str, Any]:
        model_config = self.data.get("model")
        if not isinstance(model_config, dict):
            raise ValueError("OpenLair config field 'model' must be an object")
        return model_config


def resolve_openlair_config_path(path: Path | str | None = None) -> Path:
    if path is not None:
        return Path(path).expanduser()
    configured = os.environ.get("OPENLAIR_CONFIG")
    if configured:
        return Path(configured).expanduser()
    return DEFAULT_OPENLAIR_CONFIG_PATH


def ensure_openlair_config(path: Path | str | None = None) -> Path:
    config_path = resolve_openlair_config_path(path)
    if config_path.exists():
        return config_path
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(DEFAULT_OPENLAIR_CONFIG_TEMPLATE, ensure_ascii=False, indent=2), encoding="utf-8")
    return config_path


def load_openlair_config(path: Path | str | None = None) -> OpenLairConfig:
    config_path = ensure_openlair_config(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OpenLair config must be a JSON object")
    return OpenLairConfig(path=config_path, data=data)
