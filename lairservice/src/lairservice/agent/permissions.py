from pathlib import Path
from typing import Any


DENY_LIST = ("rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda")
DESTRUCTIVE_BASH = ("rm ", "> /etc/", "chmod 777")


class PermissionPolicy:
    def __init__(self, workspace_path: Path | str) -> None:
        self._workspace_path = Path(workspace_path).resolve()

    def check(self, tool_call: dict[str, Any]) -> str | None:
        name = str(tool_call.get("name", ""))
        arguments = tool_call.get("input", {})
        if not isinstance(arguments, dict):
            return "Permission denied: invalid tool arguments"

        if name == "bash":
            command = str(arguments.get("command", ""))
            for pattern in DENY_LIST:
                if pattern in command:
                    return f"Permission denied: '{pattern}' is blocked"
            for pattern in DESTRUCTIVE_BASH:
                if pattern in command:
                    return f"Permission denied: '{pattern}' requires approval"

        if name in {"write_file", "edit_file", "read_file"}:
            path = arguments.get("path")
            if not isinstance(path, str):
                return "Permission denied: path is required"
            resolved = (self._workspace_path / path).resolve()
            if not resolved.is_relative_to(self._workspace_path):
                return "Permission denied: path escapes workspace"

        return None


def permission_hook(policy: PermissionPolicy):
    def _hook(tool_call: dict[str, Any]) -> str | None:
        return policy.check(tool_call)

    return _hook
