"""/api/keys 路由：API Key 管理（创建 / 列表 / 撤销，仅本人）。"""

from fastapi import APIRouter, Depends, Request

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import CreateApiKeyInput
from app.core.envelope import ok_response
from app.models.user import User

router = APIRouter(prefix="/keys", tags=["keys"])


@router.get("")
async def list_keys(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.api_key_service.list(user_id=user.id))


@router.post("")
async def create_key(
    request: Request, payload: CreateApiKeyInput, user: User = Depends(get_current_user)
) -> dict:
    return ok_response(
        request.app.state.api_key_service.create(user_id=user.id, name=payload.name), "创建成功"
    )


@router.delete("/{key_id}")
async def revoke_key(
    request: Request, key_id: int, user: User = Depends(get_current_user)
) -> dict:
    request.app.state.api_key_service.revoke(user_id=user.id, key_id=key_id)
    return ok_response({"ok": True}, "已撤销")
