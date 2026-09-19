# -*- coding: utf-8 -*-
"""通用文件上传：POST /upload/image（admin/officer），返回 /static/uploads 相对路径"""
from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.deps import get_db, require_roles
from app.core.response import ok
from app.models import User
from app.services.oplog import log_op
from app.utils.upload import save_image

router = APIRouter(prefix="/upload", tags=["通用上传"])


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("admin", "officer")),
    db=Depends(get_db),
):
    """上传图片（违章取证等场景）：限 jpg/png/webp、5MB；返回可直接访问的 URL"""
    url = save_image(file)
    if url:
        log_op(db, request, current_user, "上传", f"上传图片：{url}")
        db.commit()
    return ok({"url": url}, "上传成功")
