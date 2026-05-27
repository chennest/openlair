from dataclasses import dataclass

from lairservice.models.gateway import EchoModelGateway, ModelGateway, ModelRequest
from lairservice.modules.base import ModuleContext, ModuleService
from lairservice.modules.stubs import (
    accounting_service,
    calendar_service,
    habits_service,
    proactive_service,
    vocabulary_service,
)


@dataclass(frozen=True)
class AssistantServiceResult:
    message: str
    route: str


class AssistantService:
    def __init__(
        self,
        model_gateway: ModelGateway | None = None,
        module_services: dict[str, ModuleService] | None = None,
    ) -> None:
        self._model_gateway = model_gateway or EchoModelGateway()
        self._module_services = module_services or {
            "vocabulary": vocabulary_service,
            "accounting": accounting_service,
            "calendar": calendar_service,
            "habits": habits_service,
            "proactive": proactive_service,
        }

    @classmethod
    def with_notes_service(cls, notes_service: ModuleService) -> "AssistantService":
        return cls(
            module_services={
                "vocabulary": vocabulary_service,
                "accounting": accounting_service,
                "notes": notes_service,
                "calendar": calendar_service,
                "habits": habits_service,
                "proactive": proactive_service,
            }
        )

    async def handle(self, *, message: str, user_id: str, session_id: str) -> AssistantServiceResult:
        route = self._route_message(message)
        context = ModuleContext(user_id=user_id, session_id=session_id)

        module = self._module_services.get(route)
        if module is not None:
            module_message = await module.handle(message=message, context=context)
            return AssistantServiceResult(message=module_message, route=route)

        model_response = await self._model_gateway.complete(
            ModelRequest(message=message, user_id=user_id, route=route)
        )
        return AssistantServiceResult(message=model_response.message, route=route)

    def _route_message(self, message: str) -> str:
        normalized = message.lower()
        route_keywords = {
            "vocabulary": ("word", "vocab", "单词", "背词"),
            "accounting": ("expense", "spend", "账", "记账", "花了"),
            "calendar": ("calendar", "schedule", "日历", "日程", "提醒"),
            "notes": ("note", "notes", "笔记", "记录"),
            "habits": ("habit", "check in", "习惯", "打卡"),
            "proactive": ("morning", "evening", "review", "主动", "总结"),
        }
        for route, keywords in route_keywords.items():
            if any(keyword in normalized for keyword in keywords):
                return route
        return "assistant"
