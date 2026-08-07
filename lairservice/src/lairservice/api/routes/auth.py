"""/api/auth 路由：注册 / 登录 / 登出 / 当前用户。"""

from fastapi import APIRouter, Depends, Header, Request

from lairservice.api.deps import get_current_user
from lairservice.api.schemas import LoginInput, RegisterInput
from lairservice.core.envelope import ok_response
from lairservice.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(request: Request, payload: RegisterInput) -> dict:
    data = request.app.state.auth_service.register(
        name=payload.name, email=payload.email, password=payload.password
    )
    return ok_response(data, "注册成功")


@router.post("/login")
async def login(request: Request, payload: LoginInput) -> dict:
    data = request.app.state.auth_service.login(email=payload.email, password=payload.password)
    return ok_response(data, "登录成功")


@router.post("/logout")
async def logout(
    request: Request,
    _user: User = Depends(get_current_user),
    authorization: str | None = Header(default=None),
) -> dict:
    token = authorization[7:].strip() if authorization else ""
    request.app.state.auth_service.logout(token=token, user_id=_user.id)
    return ok_response({"ok": True}, "已退出登录")


@router.get("/me")
async def me(request: Request, user: User = Depends(get_current_user)) -> dict:
    return ok_response(request.app.state.auth_service.me(user_id=user.id))
