from lairservice.modules.base import ModuleContext


class StubModuleService:
    def __init__(self, name: str) -> None:
        self.name = name

    async def handle(self, *, message: str, context: ModuleContext) -> str:
        return f"{self.name} module received: {message}"


vocabulary_service = StubModuleService("vocabulary")
accounting_service = StubModuleService("accounting")
calendar_service = StubModuleService("calendar")
habits_service = StubModuleService("habits")
proactive_service = StubModuleService("proactive")
