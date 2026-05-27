from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
import asyncio

from lairservice.agent.compact import ContextCompactor


DEFAULT_MAX_TOKENS = 8_000
ESCALATED_MAX_TOKENS = 64_000
MAX_RECOVERY_RETRIES = 3
CONTINUATION_PROMPT = "Output token limit hit. Resume directly; no apology or recap."


@dataclass
class RecoveryState:
    has_escalated: bool = False
    recovery_count: int = 0
    has_attempted_reactive_compact: bool = False
    max_tokens: int = DEFAULT_MAX_TOKENS


class AgentRecovery:
    def __init__(self, compactor: ContextCompactor, max_retries: int = 3) -> None:
        self._compactor = compactor
        self._max_retries = max_retries

    async def call_with_retry(self, call: Callable[[], Awaitable[Any]]) -> Any:
        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                return await call()
            except Exception as error:
                last_error = error
                if not self.is_transient_error(error):
                    raise
                await asyncio.sleep(min(0.05 * (2**attempt), 0.5))
        if last_error is not None:
            raise last_error
        raise RuntimeError("Retry loop exited without a result")

    def recover_error(
        self,
        *,
        error: Exception,
        messages: list[dict[str, Any]],
        recovery_state: RecoveryState,
    ) -> list[dict[str, Any]] | None:
        if self.is_prompt_too_long_error(error) and not recovery_state.has_attempted_reactive_compact:
            recovery_state.has_attempted_reactive_compact = True
            return self._compactor.reactive_compact(messages)
        return None

    def recover_max_tokens(
        self,
        *,
        messages: list[dict[str, Any]],
        response_content: list[dict[str, Any]],
        recovery_state: RecoveryState,
    ) -> list[dict[str, Any]] | None:
        if not recovery_state.has_escalated:
            recovery_state.has_escalated = True
            recovery_state.max_tokens = ESCALATED_MAX_TOKENS
            return messages

        if recovery_state.recovery_count >= MAX_RECOVERY_RETRIES:
            return None

        recovery_state.recovery_count += 1
        return [
            *messages,
            {"role": "assistant", "content": response_content},
            {"role": "user", "content": CONTINUATION_PROMPT},
        ]

    def is_prompt_too_long_error(self, error: Exception) -> bool:
        message = str(error).lower()
        return (
            ("prompt" in message and "long" in message)
            or "context_length_exceeded" in message
            or "max_context_window" in message
        )

    def is_transient_error(self, error: Exception) -> bool:
        message = str(error).lower()
        name = type(error).__name__.lower()
        return "429" in message or "529" in message or "ratelimit" in name or "overloaded" in message
