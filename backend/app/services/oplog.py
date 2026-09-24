"""操作日志：关键操作（登录、增删改、审核）统一落库"""
from fastapi import Request
from sqlalchemy.orm import Session

from app.models import OpLog


def log_op(db: Session, request: Request | None, user, action: str, detail: str = "") -> None:
    """记录操作日志；user 可为 None（匿名场景）"""
    ip = ""
    if request is not None:
        ip = request.client.host if request.client else ""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
    entry = OpLog(
        user_id=user.id if user is not None else None,
        username=user.username if user is not None else "",
        action=action,
        detail=detail[:500],
        ip=ip,
    )
    db.add(entry)
    # 不在此处 commit：与业务操作同事务，保证一致性
