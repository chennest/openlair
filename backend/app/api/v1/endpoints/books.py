"""/api/books 路由：账本列表 / 建账本 / 成员增删 / 邀请码分享 / 加入 / 退出。"""

from fastapi import APIRouter, Depends, Request

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import AddMemberInput, CreateBookInput, JoinBookInput
from app.core.envelope import ok_response
from app.models.user import User

router = APIRouter(prefix="/books", tags=["books"])


@router.get("")
async def list_books(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.book_service.list(user.id))


@router.post("/join")
async def join_book(
    request: Request,
    payload: JoinBookInput,
    user: User = Depends(get_current_user),
) -> dict:
    """输入邀请码加入共享账本（任意登录用户，成为成员）。"""
    return ok_response(request.app.state.book_service.join(code=payload.code, user_id=user.id))


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


# ---------- 邀请码分享 / 加入 / 退出 ----------


@router.get("/{book_id}/invite")
async def get_invite(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.get_invite(book_id=book_id, user_id=user.id))


@router.post("/{book_id}/invite")
async def generate_invite(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """生成/重置邀请码（旧码立即失效）。"""
    return ok_response(request.app.state.book_service.generate_invite(book_id=book_id, user_id=user.id))


@router.delete("/{book_id}/invite")
async def disable_invite(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """关闭邀请（彻底停止新成员加入）。"""
    return ok_response(request.app.state.book_service.disable_invite(book_id=book_id, user_id=user.id))


@router.post("/{book_id}/leave")
async def leave_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.leave(book_id=book_id, user_id=user.id))


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


@router.post("/{book_id}/convert")
async def convert_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    """个人账本 → 共享账本（单向，不可倒转）。"""
    return ok_response(
        request.app.state.book_service.convert_to_shared(book_id=book_id, user_id=user.id)
    )


@router.delete("/{book_id}/purge")
async def purge_book(
    request: Request,
    book_id: int,
    user: User = Depends(get_current_user),
) -> dict:
    return ok_response(request.app.state.book_service.purge(book_id=book_id, user_id=user.id))
