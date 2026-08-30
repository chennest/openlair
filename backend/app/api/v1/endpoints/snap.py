"""/api/snap 路由：截图识别记账（图片 → 多模态 → 结构化结果）。"""

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.api.v1.deps import get_current_user
from app.core.envelope import ApiError, ok_response
from app.models.user import User
from app.services.snap import ALLOWED_IMAGE_MIME, MAX_IMAGE_SIZE

router = APIRouter(prefix="/snap", tags=["snap"])


@router.post("/parse")
async def parse_snap(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> dict:
    """识别截图中的记账信息，返回 { type, amount, category, note, date, confidence }。"""
    mime = (file.content_type or "").lower()
    if mime not in ALLOWED_IMAGE_MIME:
        raise ApiError(400, "仅支持 JPG/PNG/WebP 图片")
    data = await file.read()
    if len(data) > MAX_IMAGE_SIZE:
        raise ApiError(400, "图片不能超过 10MB")
    if len(data) == 0:
        raise ApiError(400, "图片内容为空")
    result = await request.app.state.snap_parser.parse(image_bytes=data, mime=mime)
    return ok_response(result, "识别成功")
