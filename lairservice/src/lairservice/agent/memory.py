from pathlib import Path
from typing import Any
import re

from lairservice.agent.skills import parse_frontmatter


class MemoryStore:
    def __init__(self, memory_path: Path | str) -> None:
        self._memory_path = Path(memory_path)
        self._memory_path.mkdir(parents=True, exist_ok=True)
        self._index_path = self._memory_path / "MEMORY.md"
        self._rebuild_index()

    def index(self) -> str:
        if not self._index_path.exists():
            return ""
        return self._index_path.read_text(encoding="utf-8").strip()

    def load_relevant(self, messages: list[dict[str, Any]], max_items: int = 5) -> str:
        query = " ".join(self._recent_user_text(messages)).lower()
        if not query.strip():
            return ""
        selected = []
        for path in sorted(self._memory_path.glob("*.md")):
            if path.name == "MEMORY.md":
                continue
            raw = path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(raw)
            haystack = f"{metadata.get('name', path.stem)} {metadata.get('description', '')}".lower()
            if any(word in haystack for word in query.split() if len(word) > 3):
                selected.append(raw)
            if len(selected) >= max_items:
                break
        if not selected:
            return ""
        return "<relevant_memories>\n" + "\n\n".join(selected) + "\n</relevant_memories>"

    def extract_from_messages(self, messages: list[dict[str, Any]]) -> int:
        count = 0
        for text in self._recent_user_text(messages):
            match = re.search(r"remember(?: that)?\s+(.+)", text, re.IGNORECASE)
            if match is None:
                continue
            body = match.group(1).strip()
            if not body:
                continue
            name = re.sub(r"[^a-z0-9]+", "-", body.lower())[:48].strip("-") or "memory"
            self.write(name=name, memory_type="user", description=body[:100], body=body)
            count += 1
        return count

    def write(self, *, name: str, memory_type: str, description: str, body: str) -> Path:
        slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "memory"
        path = self._memory_path / f"{slug}.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {description}\ntype: {memory_type}\n---\n\n{body}\n",
            encoding="utf-8",
        )
        self._rebuild_index()
        return path

    def _rebuild_index(self) -> None:
        lines = []
        for path in sorted(self._memory_path.glob("*.md")):
            if path.name == "MEMORY.md":
                continue
            raw = path.read_text(encoding="utf-8")
            metadata, body = parse_frontmatter(raw)
            name = metadata.get("name", path.stem)
            description = metadata.get("description", body.splitlines()[0][:80] if body else "")
            lines.append(f"- [{name}]({path.name}) — {description}")
        self._index_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def _recent_user_text(self, messages: list[dict[str, Any]]) -> list[str]:
        texts = []
        for message in reversed(messages):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str):
                texts.append(content)
            if len(texts) >= 5:
                break
        return list(reversed(texts))
