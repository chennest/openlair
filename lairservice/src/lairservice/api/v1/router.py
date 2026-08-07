"""API v1 路由组装：统一挂 /api 前缀（与前端 mock 契约一致）。"""

from fastapi import APIRouter

from lairservice.api.v1.endpoints.auth import router as auth_router
from lairservice.api.v1.endpoints.books import router as books_router
from lairservice.api.v1.endpoints.ledger import router as ledger_router
from lairservice.api.v1.endpoints.modules import (
    calendar_router,
    habits_router,
    notes_router,
    overview_router,
    todo_router,
)

v1_router = APIRouter(prefix="/api")
v1_router.include_router(auth_router)
v1_router.include_router(ledger_router)
v1_router.include_router(books_router)
v1_router.include_router(todo_router)
v1_router.include_router(calendar_router)
v1_router.include_router(notes_router)
v1_router.include_router(habits_router)
v1_router.include_router(overview_router)
