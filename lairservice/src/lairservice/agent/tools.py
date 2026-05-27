from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import glob as glob_module
import subprocess


ToolHandler = Callable[..., str]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]

    def as_model_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


DynamicToolProvider = Callable[[], tuple[list[ToolDefinition], dict[str, ToolHandler]]]


@dataclass
class TodoStore:
    todos: list[dict[str, str]] = field(default_factory=list)

    def update(self, todos: list[dict[str, str]]) -> str:
        for index, todo in enumerate(todos):
            if "content" not in todo or "status" not in todo:
                return f"Error: todos[{index}] missing content or status"
            if todo["status"] not in {"pending", "in_progress", "completed"}:
                return f"Error: todos[{index}] has invalid status {todo['status']}"
        self.todos = todos
        return f"Updated {len(todos)} tasks"


@dataclass
class ToolRegistry:
    _definitions: dict[str, ToolDefinition] = field(default_factory=dict)
    _handlers: dict[str, ToolHandler] = field(default_factory=dict)
    _dynamic_providers: list[DynamicToolProvider] = field(default_factory=list)

    def register(self, definition: ToolDefinition, handler: ToolHandler) -> None:
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler

    def register_dynamic_provider(self, provider: DynamicToolProvider) -> None:
        self._dynamic_providers.append(provider)

    def definitions(self) -> list[dict[str, Any]]:
        definitions = list(self._definitions.values())
        for provider in self._dynamic_providers:
            dynamic_definitions, _handlers = provider()
            definitions.extend(dynamic_definitions)
        return [definition.as_model_tool() for definition in definitions]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        handlers = dict(self._handlers)
        for provider in self._dynamic_providers:
            _definitions, dynamic_handlers = provider()
            handlers.update(dynamic_handlers)
        handler = handlers.get(name)
        if handler is None:
            return f"Unknown tool: {name}"
        try:
            return handler(**arguments)
        except TypeError as error:
            return f"Error: invalid arguments for {name}: {error}"


class WorkspaceTools:
    def __init__(self, workspace_path: Path | str, todo_store: TodoStore | None = None) -> None:
        self._workspace_path = Path(workspace_path).resolve()
        self._todo_store = todo_store or TodoStore()

    @property
    def todo_store(self) -> TodoStore:
        return self._todo_store

    def safe_path(self, path: str) -> Path:
        resolved = (self._workspace_path / path).resolve()
        if not resolved.is_relative_to(self._workspace_path):
            raise ValueError(f"Path escapes workspace: {path}")
        return resolved

    def bash(self, command: str, run_in_background: bool = False) -> str:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._workspace_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            return "Error: Timeout (120s)"
        except OSError as error:
            return f"Error: {error}"

        output = (result.stdout + result.stderr).strip()
        return output[:50_000] if output else "(no output)"

    def read_file(self, path: str, limit: int | None = None) -> str:
        try:
            lines = self.safe_path(path).read_text(encoding="utf-8").splitlines()
        except OSError as error:
            return f"Error: {error}"
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)

    def write_file(self, path: str, content: str) -> str:
        try:
            target = self.safe_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        except (OSError, ValueError) as error:
            return f"Error: {error}"
        return f"Wrote {len(content)} bytes to {path}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        try:
            target = self.safe_path(path)
            text = target.read_text(encoding="utf-8")
            if old_text not in text:
                return f"Error: text not found in {path}"
            target.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        except (OSError, ValueError) as error:
            return f"Error: {error}"
        return f"Edited {path}"

    def glob(self, pattern: str) -> str:
        matches = []
        for match in glob_module.glob(pattern, root_dir=self._workspace_path):
            if (self._workspace_path / match).resolve().is_relative_to(self._workspace_path):
                matches.append(match)
        return "\n".join(matches) if matches else "(no matches)"

    def todo_write(self, todos: list[dict[str, str]]) -> str:
        return self._todo_store.update(todos)


def create_workspace_tool_registry(workspace_tools: WorkspaceTools) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="bash",
            description="Run a shell command in the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "run_in_background": {"type": "boolean"},
                },
                "required": ["command"],
            },
        ),
        workspace_tools.bash,
    )
    registry.register(
        ToolDefinition(
            name="read_file",
            description="Read a file from the workspace.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}},
                "required": ["path"],
            },
        ),
        workspace_tools.read_file,
    )
    registry.register(
        ToolDefinition(
            name="write_file",
            description="Write content to a workspace file.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        ),
        workspace_tools.write_file,
    )
    registry.register(
        ToolDefinition(
            name="edit_file",
            description="Replace exact text in a workspace file once.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        ),
        workspace_tools.edit_file,
    )
    registry.register(
        ToolDefinition(
            name="glob",
            description="Find workspace files matching a glob pattern.",
            input_schema={"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]},
        ),
        workspace_tools.glob,
    )
    registry.register(
        ToolDefinition(
            name="todo_write",
            description="Create and update a task list for the current agent session.",
            input_schema={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            },
                            "required": ["content", "status"],
                        },
                    }
                },
                "required": ["todos"],
            },
        ),
        workspace_tools.todo_write,
    )
    return registry
