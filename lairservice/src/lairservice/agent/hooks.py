from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


HookCallback = Callable[..., str | None]


@dataclass
class HookRegistry:
    _hooks: dict[str, list[HookCallback]] = field(
        default_factory=lambda: {
            "UserPromptSubmit": [],
            "PreToolUse": [],
            "PostToolUse": [],
            "Stop": [],
        }
    )

    def register(self, event: str, callback: HookCallback) -> None:
        self._hooks.setdefault(event, []).append(callback)

    def trigger(self, event: str, *args: Any) -> str | None:
        for callback in self._hooks.get(event, []):
            result = callback(*args)
            if result is not None:
                return result
        return None


def large_output_hook(_tool_call: dict[str, Any], output: str) -> str | None:
    if len(output) > 100_000:
        return f"Large tool output truncated warning: {len(output)} characters"
    return None
