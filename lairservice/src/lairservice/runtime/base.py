from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AssistantResponse:
    message: str
    session_id: str
    route: str


class AssistantRuntime(Protocol):
    async def invoke(self, *, message: str, user_id: str, session_id: str) -> AssistantResponse:
        """Run one assistant turn through the configured runtime."""
