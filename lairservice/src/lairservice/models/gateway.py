from dataclasses import dataclass, field
from copy import deepcopy
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import asyncio
import json
import os

from lairservice.models.config import ModelGatewayConfig, ProviderConfig, load_model_gateway_config


@dataclass(frozen=True)
class ModelRequest:
    message: str
    user_id: str
    route: str


@dataclass(frozen=True)
class ModelResponse:
    message: str
    provider: str
    model: str


@dataclass(frozen=True)
class AgentModelRequest:
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]]
    system: str
    user_id: str
    session_id: str
    max_tokens: int = 8_000


@dataclass(frozen=True)
class AgentModelResponse:
    content: list[dict[str, Any]]
    stop_reason: str
    provider: str
    model: str


class ModelGateway(Protocol):
    async def complete(self, request: ModelRequest) -> ModelResponse:
        """Generate a model response through the configured provider/model route."""
        ...

    async def create_agent_response(self, request: AgentModelRequest) -> AgentModelResponse:
        """Generate one agent-loop response with optional tool-use blocks."""
        ...


class ConfiguredModelGateway:
    def __init__(self, config: ModelGatewayConfig) -> None:
        self._config = config
        self._clients = {name: _client_for_provider(provider) for name, provider in config.providers.items()}

    async def complete(self, request: ModelRequest) -> ModelResponse:
        provider = self._config.provider_for_route(request.route)
        client = self._clients[provider.name]
        return await client.complete(request, provider)

    async def create_agent_response(self, request: AgentModelRequest) -> AgentModelResponse:
        provider = self._config.provider_for_route("agent")
        client = self._clients[provider.name]
        return await client.create_agent_response(request, provider)


class _ProviderClient(Protocol):
    async def complete(self, request: ModelRequest, provider: ProviderConfig) -> ModelResponse:
        ...

    async def create_agent_response(self, request: AgentModelRequest, provider: ProviderConfig) -> AgentModelResponse:
        ...


class _OpenAICompatibleProviderClient:
    async def complete(self, request: ModelRequest, provider: ProviderConfig) -> ModelResponse:
        payload = {
            "model": provider.model,
            "messages": [{"role": "user", "content": request.message}],
        }
        data = await asyncio.to_thread(_post_openai_compatible, provider, payload)
        message = _extract_openai_text(data)
        return ModelResponse(message=message, provider=provider.name, model=provider.model)

    async def create_agent_response(self, request: AgentModelRequest, provider: ProviderConfig) -> AgentModelResponse:
        payload: dict[str, Any] = {
            "model": provider.model,
            "messages": _to_openai_messages(request.messages, request.system),
            "tools": [_to_openai_tool(tool) for tool in request.tools],
            "max_tokens": request.max_tokens,
        }
        data = await asyncio.to_thread(_post_openai_compatible, provider, payload)
        return _to_agent_response(data, provider)


def create_model_gateway_from_config(path: Path | str | None) -> ModelGateway:
    if path is None:
        raise ValueError("Model config is required. Set LAIR_MODEL_CONFIG or pass model_config_path.")
    config_path = Path(path)
    if not config_path.exists():
        raise ValueError(f"Model config file does not exist: {config_path}")
    return ConfiguredModelGateway(load_model_gateway_config(config_path))


def _client_for_provider(provider: ProviderConfig) -> _ProviderClient:
    if provider.kind == "openai_compatible":
        return _OpenAICompatibleProviderClient()
    raise ValueError(f"Unsupported model provider kind {provider.kind!r}")


def _post_openai_compatible(provider: ProviderConfig, payload: dict[str, Any]) -> dict[str, Any]:
    if provider.base_url is None:
        raise ValueError(f"Provider {provider.name!r} requires base_url")
    api_key = os.environ.get(provider.api_key_env or "") if provider.api_key_env else None
    if provider.api_key_env and not api_key:
        raise ValueError(f"Environment variable {provider.api_key_env!r} is required for provider {provider.name!r}")
    url = provider.base_url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=provider.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Model provider {provider.name} HTTP {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError(f"Model provider {provider.name} request failed: {error.reason}") from error


def _to_openai_messages(messages: list[dict[str, Any]], system: str) -> list[dict[str, str]]:
    converted = [{"role": "system", "content": system}]
    for message in messages:
        converted.append({"role": str(message.get("role", "user")), "content": _content_to_text(message.get("content"))})
    return converted


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(str(block.get("text", "")))
            elif isinstance(block, dict) and block.get("type") == "tool_result":
                texts.append(f"Tool result {block.get('tool_use_id')}: {block.get('content')}")
            else:
                texts.append(json.dumps(block, ensure_ascii=False))
        return "\n".join(texts)
    return json.dumps(content, ensure_ascii=False)


def _to_openai_tool(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _extract_openai_text(data: dict[str, Any]) -> str:
    choices = data.get("choices", [])
    if not choices:
        return ""
    message = choices[0].get("message", {})
    return str(message.get("content") or "")


def _to_agent_response(data: dict[str, Any], provider: ProviderConfig) -> AgentModelResponse:
    choices = data.get("choices", [])
    if not choices:
        return AgentModelResponse(content=[], stop_reason="end_turn", provider=provider.name, model=provider.model)
    choice = choices[0]
    message = choice.get("message", {})
    content: list[dict[str, Any]] = []
    text = message.get("content")
    if text:
        content.append({"type": "text", "text": str(text)})
    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function", {})
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}
        content.append(
            {
                "type": "tool_use",
                "id": str(tool_call.get("id", f"tool-{len(content) + 1}")),
                "name": str(function.get("name", "")),
                "input": arguments,
            }
        )
    finish_reason = choice.get("finish_reason")
    stop_reason = "tool_use" if message.get("tool_calls") else "end_turn"
    if finish_reason == "length":
        stop_reason = "max_tokens"
    return AgentModelResponse(content=content, stop_reason=stop_reason, provider=provider.name, model=provider.model)


@dataclass
class ScriptedAgentModelGateway:
    responses: list[AgentModelResponse]
    calls: list[AgentModelRequest] = field(default_factory=list)

    async def complete(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(message=f"[{request.route}] {request.message}", provider="local", model="scripted")

    async def create_agent_response(self, request: AgentModelRequest) -> AgentModelResponse:
        self.calls.append(
            AgentModelRequest(
                messages=deepcopy(request.messages),
                tools=deepcopy(request.tools),
                system=request.system,
                user_id=request.user_id,
                session_id=request.session_id,
                max_tokens=request.max_tokens,
            )
        )
        if not self.responses:
            return AgentModelResponse(
                content=[{"type": "text", "text": "No scripted response remaining."}],
                stop_reason="end_turn",
                provider="local",
                model="scripted",
            )
        return self.responses.pop(0)
