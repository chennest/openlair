"""/api/ledger 路由：分类 / 流水列表 / 趋势 / 预算 / 增删改。"""

from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from lairservice.api.deps import get_current_user
from lairservice.api.schemas import CreateTransactionInput, UpdateBudgetInput, UpdateTransactionInput
from lairservice.core.envelope import ok_response
from lairservice.models.user import User

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("/categories")
async def categories(
    request: Request,
    type: str | None = None,
    _user: User = Depends(get_current_user),
) -> dict:
    data = request.app.state.ledger_service.categories(type)
    return ok_response(data)


@router.get("")
async def list_transactions(
    request: Request,
    bookId: int | None = Query(default=None),
    type: str | None = None,
    categoryId: int | None = Query(default=None),
    keyword: str | None = None,
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=200),
    _user: User = Depends(get_current_user),
) -> dict:
    data = request.app.state.ledger_service.list_transactions(
        book_id=bookId,
        type=type,
        category_id=categoryId,
        keyword=keyword,
        start_date=startDate,
        end_date=endDate,
        page=page,
        page_size=pageSize,
    )
    return ok_response(data)


@router.get("/trend")
async def trend(
    request: Request,
    bookId: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.ledger_service.trend(book_id=bookId))


@router.get("/budget")
async def get_budget(
    request: Request,
    bookId: int | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.ledger_service.get_budget(book_id=bookId))


@router.put("/budget")
async def update_budget(
    request: Request,
    payload: UpdateBudgetInput,
    _user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.ledger_service.update_budget(book_id=payload.bookId, amount=payload.amount)
    )


@router.post("")
async def create(
    request: Request,
    payload: CreateTransactionInput,
    user: User = Depends(get_current_user),
) -> dict:
    data = request.app.state.ledger_service.create(
        user_id=user.id,
        type=payload.type,
        category_id=payload.categoryId,
        amount=payload.amount,
        date=payload.date,
        note=payload.note,
        book_id=payload.bookId,
    )
    return ok_response(data)


@router.put("/{transaction_id}")
async def update(
    request: Request,
    transaction_id: int,
    payload: UpdateTransactionInput,
    user: User = Depends(get_current_user),
) -> dict:
    patch = payload.model_dump(exclude_unset=True)
    return ok_response(
        request.app.state.ledger_service.update(user_id=user.id, transaction_id=transaction_id, patch=patch)
    )


@router.delete("/{transaction_id}")
async def remove(
    request: Request,
    transaction_id: int,
    _user: User = Depends(get_current_user),
) -> dict:
    request.app.state.ledger_service.remove(transaction_id=transaction_id)
    return ok_response({"ok": True})
