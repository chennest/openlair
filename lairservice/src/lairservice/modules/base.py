from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ModuleContext:
    user_id: str
    session_id: str


class ModuleService(Protocol):
    name: str

    async def handle(self, *, message: str, context: ModuleContext) -> str:
        """Handle a routed assistant request for this product module."""
