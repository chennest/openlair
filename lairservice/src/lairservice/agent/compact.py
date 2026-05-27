from pathlib import Path
from typing import Any
import json
import time


class ContextCompactor:
    def __init__(
        self,
        workspace_path: Path | str,
        context_limit: int = 50_000,
        keep_recent_tool_results: int = 3,
        persist_threshold: int = 30_000,
    ) -> None:
        self._workspace_path = Path(workspace_path)
        self._context_limit = context_limit
        self._keep_recent_tool_results = keep_recent_tool_results
        self._persist_threshold = persist_threshold
        self._transcript_path = self._workspace_path / ".transcripts"
        self._tool_results_path = self._workspace_path / ".task_outputs" / "tool-results"

    def compact_before_model(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        compacted = self.tool_result_budget(messages)
        compacted = self.snip_compact(compacted)
        compacted = self.micro_compact(compacted)
        if self.estimate_size(compacted) > self._context_limit:
            compacted = self.compact_history(compacted, label="Compacted")
        return compacted

    def reactive_compact(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.compact_history(messages, label="Reactive compact", tail=5)

    def estimate_size(self, messages: list[dict[str, Any]]) -> int:
        return len(str(messages))

    def snip_compact(self, messages: list[dict[str, Any]], max_messages: int = 50) -> list[dict[str, Any]]:
        if len(messages) <= max_messages:
            return messages
        head_count = 3
        tail_count = max_messages - head_count
        snipped = len(messages) - head_count - tail_count
        return [
            *messages[:head_count],
            {"role": "user", "content": f"[snipped {snipped} messages]"},
            *messages[-tail_count:],
        ]

    def micro_compact(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        copied = self._copy_messages(messages)
        tool_results = self._collect_tool_results(copied)
        if len(tool_results) <= self._keep_recent_tool_results:
            return copied
        for block in tool_results[: -self._keep_recent_tool_results]:
            content = str(block.get("content", ""))
            if len(content) > 120:
                block["content"] = "[Earlier tool result compacted. Re-run if needed.]"
        return copied

    def tool_result_budget(self, messages: list[dict[str, Any]], max_bytes: int = 200_000) -> list[dict[str, Any]]:
        copied = self._copy_messages(messages)
        if not copied:
            return copied
        last = copied[-1]
        content = last.get("content")
        if last.get("role") != "user" or not isinstance(content, list):
            return copied
        blocks = [block for block in content if isinstance(block, dict) and block.get("type") == "tool_result"]
        total = sum(len(str(block.get("content", ""))) for block in blocks)
        if total <= max_bytes:
            return copied
        for block in sorted(blocks, key=lambda item: len(str(item.get("content", ""))), reverse=True):
            if total <= max_bytes:
                break
            raw = str(block.get("content", ""))
            if len(raw) <= self._persist_threshold:
                continue
            block["content"] = self._persist_large_output(str(block.get("tool_use_id", "unknown")), raw)
            total = sum(len(str(item.get("content", ""))) for item in blocks)
        return copied

    def compact_history(
        self,
        messages: list[dict[str, Any]],
        *,
        label: str,
        tail: int | None = None,
    ) -> list[dict[str, Any]]:
        transcript = self.write_transcript(messages)
        summary = self._summarize(messages)
        compacted = [{"role": "user", "content": f"[{label}]\nTranscript: {transcript}\n\n{summary}"}]
        if tail is not None:
            compacted.extend(messages[-tail:])
        return compacted

    def write_transcript(self, messages: list[dict[str, Any]]) -> Path:
        self._transcript_path.mkdir(parents=True, exist_ok=True)
        path = self._transcript_path / f"transcript_{int(time.time())}.jsonl"
        with path.open("w", encoding="utf-8") as file:
            for message in messages:
                file.write(json.dumps(message, ensure_ascii=False, default=str) + "\n")
        return path

    def _persist_large_output(self, tool_use_id: str, output: str) -> str:
        self._tool_results_path.mkdir(parents=True, exist_ok=True)
        path = self._tool_results_path / f"{tool_use_id}.txt"
        if not path.exists():
            path.write_text(output, encoding="utf-8")
        return f"<persisted-output>\nFull output: {path}\nPreview:\n{output[:2000]}\n</persisted-output>"

    def _collect_tool_results(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for message in messages:
            content = message.get("content")
            if message.get("role") != "user" or not isinstance(content, list):
                continue
            blocks.extend(block for block in content if isinstance(block, dict) and block.get("type") == "tool_result")
        return blocks

    def _summarize(self, messages: list[dict[str, Any]]) -> str:
        recent = messages[-8:]
        return "Summary placeholder preserving recent context:\n" + json.dumps(recent, ensure_ascii=False, default=str)[:4000]

    def _copy_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return json.loads(json.dumps(messages, ensure_ascii=False, default=str))
