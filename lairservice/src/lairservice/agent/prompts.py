from dataclasses import dataclass
from typing import Any
import json

from lairservice.agent.memory import MemoryStore
from lairservice.agent.skills import SkillRegistry
from lairservice.agent.tools import ToolRegistry


@dataclass
class SystemPromptBuilder:
    workspace: str
    tools: ToolRegistry
    skills: SkillRegistry
    memory: MemoryStore
    _last_key: str | None = None
    _last_prompt: str | None = None

    def build(self, context: dict[str, Any]) -> str:
        key = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
        if key == self._last_key and self._last_prompt is not None:
            return self._last_prompt

        sections = [
            "You are Lair's coding-agent harness runtime. Act through tools; do not emulate tools in prose.",
            "Before multi-step work, use todo_write. For complex side work, use task to spawn a subagent.",
            f"Working directory: {self.workspace}",
            "Available tools: " + ", ".join(tool["name"] for tool in self.tools.definitions()),
            "Skills available:\n" + self.skills.catalog(),
        ]
        memory_index = context.get("memory_index") or self.memory.index()
        if memory_index:
            sections.append("Memories available:\n" + memory_index)
        relevant_memories = context.get("relevant_memories")
        if relevant_memories:
            sections.append(str(relevant_memories))

        self._last_key = key
        self._last_prompt = "\n\n".join(sections)
        return self._last_prompt
