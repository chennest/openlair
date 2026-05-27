from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import re

from lairservice.agent.tools import ToolDefinition, ToolHandler


_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_mcp_name(name: str) -> str:
    return _DISALLOWED_CHARS.sub("_", name)


@dataclass
class MCPClient:
    name: str
    tools: list[ToolDefinition] = field(default_factory=list)
    _handlers: dict[str, ToolHandler] = field(default_factory=dict)

    def register(self, tool_defs: list[ToolDefinition], handlers: dict[str, ToolHandler]) -> None:
        self.tools = tool_defs
        self._handlers = handlers

    def call_tool(self, tool_name: str, args: dict[str, object]) -> str:
        handler = self._handlers.get(tool_name)
        if handler is None:
            return f"MCP error: unknown tool '{tool_name}'"
        try:
            return handler(**args)
        except TypeError as error:
            return f"MCP error: invalid arguments for {tool_name}: {error}"
        except Exception as error:
            return f"MCP error: {error}"


class MCPPluginManager:
    def __init__(self) -> None:
        self._clients: dict[str, MCPClient] = {}
        self._server_factories: dict[str, Callable[[], MCPClient]] = {
            "docs": _mock_server_docs,
            "deploy": _mock_server_deploy,
        }

    def connect_mcp(self, name: str) -> str:
        server_name = normalize_mcp_name(name)
        factory = self._server_factories.get(server_name)
        if factory is None:
            available = ", ".join(sorted(self._server_factories))
            return f"Error: unknown MCP server {name}. Available: {available}"
        self._clients[server_name] = factory()
        tool_names = [f"mcp__{server_name}__{normalize_mcp_name(tool.name)}" for tool in self._clients[server_name].tools]
        return f"Connected MCP server {server_name}. Tools: {', '.join(tool_names)}"

    def assemble_tool_pool(self) -> tuple[list[ToolDefinition], dict[str, ToolHandler]]:
        definitions: list[ToolDefinition] = []
        handlers: dict[str, ToolHandler] = {}
        for server_name, client in self._clients.items():
            safe_server = normalize_mcp_name(server_name)
            for tool in client.tools:
                safe_tool = normalize_mcp_name(tool.name)
                prefixed = f"mcp__{safe_server}__{safe_tool}"
                definitions.append(
                    ToolDefinition(
                        name=prefixed,
                        description=tool.description,
                        input_schema=tool.input_schema,
                    )
                )
                handlers[prefixed] = _make_mcp_handler(client, tool.name)
        return definitions, handlers


def _make_mcp_handler(client: MCPClient, tool_name: str) -> ToolHandler:
    def handler(**kwargs: object) -> str:
        return client.call_tool(tool_name, kwargs)

    return handler


def _mock_server_docs() -> MCPClient:
    client = MCPClient("docs")
    client.register(
        [
            ToolDefinition(
                name="search",
                description="(readOnly) Search project documentation.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            ToolDefinition(
                name="get_version",
                description="(readOnly) Return the docs API version.",
                input_schema={"type": "object", "properties": {}},
            ),
        ],
        {
            "search": lambda query: f"Docs result for: {query}",
            "get_version": lambda: "docs-api 1.0",
        },
    )
    return client


def _mock_server_deploy() -> MCPClient:
    client = MCPClient("deploy")
    client.register(
        [
            ToolDefinition(
                name="trigger",
                description="(destructive) Trigger a deployment.",
                input_schema={
                    "type": "object",
                    "properties": {"environment": {"type": "string"}},
                    "required": ["environment"],
                },
            ),
            ToolDefinition(
                name="status",
                description="(readOnly) Return deployment status.",
                input_schema={"type": "object", "properties": {}},
            ),
        ],
        {
            "trigger": lambda environment: f"Deployment triggered for {environment}",
            "status": lambda: "deploy status: idle",
        },
    )
    return client
