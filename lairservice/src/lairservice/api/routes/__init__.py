"""API 路由组装：业务路由统一挂 /api 前缀（与前端 mock 契约一致）。"""

from fastapi import APIRouter

from lairservice.api.routes.auth import router as auth_router
from lairservice.api.routes.books import router as books_router
from lairservice.api.routes.ledger import router as ledger_router
from lairservice.api.routes.modules import (
    calendar_router,
    habits_router,
    notes_router,
    overview_router,
    todo_router,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(ledger_router)
api_router.include_router(books_router)
api_router.include_router(todo_router)
api_router.include_router(calendar_router)
api_router.include_router(notes_router)
api_router.include_router(habits_router)
api_router.include_router(overview_router)