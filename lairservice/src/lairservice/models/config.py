from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    kind: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class ModelGatewayConfig:
    default_route: str
    routes: dict[str, str]
    providers: dict[str, ProviderConfig]

    def provider_for_route(self, route: str) -> ProviderConfig:
        provider_name = self.routes.get(route) or self.routes.get(self.default_route)
        if provider_name is None:
            raise ValueError(f"No provider configured for route {route!r} and default route {self.default_route!r}")
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ValueError(f"Route {route!r} references unknown provider {provider_name!r}")
        return provider


def load_model_gateway_config(path: Path | str) -> ModelGatewayConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Model config must be a JSON object")

    default_route = _required_str(data, "default_route")
    routes_data = data.get("routes", {})
    providers_data = data.get("providers", {})
    if not isinstance(routes_data, dict):
        raise ValueError("Model config routes must be an object")
    if not isinstance(providers_data, dict):
        raise ValueError("Model config providers must be an object")

    providers: dict[str, ProviderConfig] = {}
    for name, provider_data in providers_data.items():
        if not isinstance(name, str) or not isinstance(provider_data, dict):
            raise ValueError("Each provider entry must be an object")
        providers[name] = ProviderConfig(
            name=name,
            kind=_required_str(provider_data, "kind"),
            model=_required_str(provider_data, "model"),
            base_url=_optional_str(provider_data, "base_url"),
            api_key_env=_optional_str(provider_data, "api_key_env"),
            timeout_seconds=float(provider_data.get("timeout_seconds", 60.0)),
        )

    routes = {str(route): str(provider_name) for route, provider_name in routes_data.items()}
    if default_route not in routes:
        raise ValueError(f"Default route {default_route!r} must exist in routes")
    config = ModelGatewayConfig(default_route=default_route, routes=routes, providers=providers)
    config.provider_for_route(default_route)
    return config


def _required_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Model config field {key!r} must be a non-empty string")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"Model config field {key!r} must be a non-empty string when provided")
    return value
