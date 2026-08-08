"""/api/books 路由：账本列表 / 建账本 / 成员增删。"""

from fastapi import APIRouter, Depends, Request

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import AddMemberInput, CreateBookInput
from app.core.envelope import ok_response
from app.models.user import User

router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.book_service.list(user.id))


@router.post("")
async def create_book(
    request: Request,
    payload: CreateBookInput,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.book_service.create(user_id=user.id, name=payload.name, type=payload.type)
    )


@router.post("/{book_id}/members")
async def add_member(
    request: Request,
    book_id: int,
    payload: AddMemberInput,
    _user: User = Depends(get_current_user),
) -> dict:
    return ok_response(
        request.app.state.book_service.add_member(book_id=book_id, user_id=payload.userId, name=payload.name)
    )


@router.delete("/{book_id}/members/{user_id}")
async def remove_member(
    request: Request,
    book_id: int,
    user_id: int,
    _user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.remove_member(book_id=book_id, user_id=user_id))


# ---------- 回收站（软删除） ----------


@router.get("/trash")
async def list_trash(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.book_service.trash(user.id))


@router.delete("/{book_id}")
async def soft_delete_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.soft_delete(book_id=book_id, user_id=user.id))


@router.post("/{book_id}/restore")
async def restore_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.restore(book_id=book_id, user_id=user.id))


@router.delete("/{book_id}/purge")
async def purge_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.purge(book_id=book_id, user_id=user.id))
