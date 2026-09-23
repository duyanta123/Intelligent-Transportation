"""车牌识别路由：POST /lpr/recognize（multipart 上传，10 秒超时保护）"""
import logging
import os

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.core.deps import get_db, require_roles
from app.core.response import E_LPR_FAILED, E_UPLOAD, BizError, ok
from app.models import User
from app.services.lpr_service import recognize_plate
from app.services.oplog import log_op
from app.utils.validators import UPLOAD_MAX_BYTES, UPLOAD_SUFFIXES, is_image_bytes

logger = logging.getLogger("smart-traffic.lpr")

router = APIRouter(prefix="/lpr", tags=["车牌识别"])


@router.post("/recognize")
def recognize(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "officer")),
    db=Depends(get_db),
):
    """上传车辆图片识别车牌，返回车牌号与置信度；失败时提示手动录入。

    同步端点：推理在单 worker 线程池中执行，async 会把事件循环阻塞最长 20 秒。
    """
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in UPLOAD_SUFFIXES:
        raise BizError(*E_UPLOAD)
    content = file.file.read(UPLOAD_MAX_BYTES + 1)
    if not content or len(content) > UPLOAD_MAX_BYTES:
        raise BizError(*E_UPLOAD)
    if not is_image_bytes(content):
        # 扩展名可伪造，按文件头二次校验
        raise BizError(*E_UPLOAD)
    try:
        result = recognize_plate(content)
    except Exception as err:
        logger.warning("车牌识别失败：%s", err)
        raise BizError(*E_LPR_FAILED) from err
    log_op(db, request, current_user, "识别", f"车牌识别：{result['plate_no']}（置信度 {result['confidence']}）")
    db.commit()
    return ok(result, "识别成功")
