# -*- coding: utf-8 -*-
"""上传文件工具：图片保存（限 5MB、jpg/png/webp），供停车入场与通用上传共用"""
import os
import time

from fastapi import UploadFile

from app.core.config import settings
from app.core.response import E_UPLOAD, BizError
from app.utils.validators import UPLOAD_MAX_BYTES, UPLOAD_SUFFIXES, is_image_bytes


def save_image(file: UploadFile | None) -> str:
    """保存图片到 uploads 目录，返回 /static/uploads 相对路径；空文件返回空串"""
    if file is None:
        return ""
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise BizError(*E_UPLOAD)
    content = file.file.read(UPLOAD_MAX_BYTES + 1)
    if len(content) > UPLOAD_MAX_BYTES:
        raise BizError(*E_UPLOAD)
    if not content:
        return ""
    if not is_image_bytes(content):
        # 扩展名可伪造，按文件头二次校验，拒绝伪装成图片的任意文件
        raise BizError(*E_UPLOAD)
    upload_dir = os.path.join(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{time.strftime('%Y%m%d%H%M%S')}_{time.time_ns() % 1000000}{suffix}"
    with open(os.path.join(upload_dir, filename), "wb") as f:
        f.write(content)
    return f"/static/uploads/{filename}"
