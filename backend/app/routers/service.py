"""公共服务：公告管理（admin 发布）、投诉反馈（user 提交 / officer 受理处理）"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import E_FEEDBACK_HANDLED, E_NOT_FOUND, BizError, ok
from app.models import Feedback, Notice, User
from app.schemas import FeedbackHandleIn, FeedbackIn, NoticeIn
from app.services.oplog import log_op
from app.utils.validators import clamp_page

router = APIRouter(tags=["公共服务"])


# ---------------- 公告 ----------------
@router.get("/notices")
def list_notices(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
    db: Session = Depends(get_db),
):
    """公告列表：非管理员仅可见已发布公告"""
    page, size = clamp_page(page, size)
    query = db.query(Notice).filter(Notice.is_deleted == 0)
    if _role_of(db, current_user) != "admin":
        query = query.filter(Notice.status == 1)
    total = query.count()
    # MySQL 无 NULLS LAST：用 COALESCE(published_at, created_at) 兜底排序
    rows = (
        query.order_by(func.coalesce(Notice.published_at, Notice.created_at).desc(), Notice.id.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return ok({"list": [_notice_out(n) for n in rows], "total": total, "page": page, "size": size})


def _role_of(db: Session, user: User) -> str:
    from app.services.auth_service import get_user_role_code

    return get_user_role_code(db, user)


def _notice_out(n: Notice) -> dict:
    return {
        "id": n.id,
        "title": n.title,
        "content": n.content,
        "status": n.status,
        "publisher_id": n.publisher_id,
        "published_at": n.published_at.strftime("%Y-%m-%d %H:%M:%S") if n.published_at else None,
        "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/notices")
def create_notice(
    body: NoticeIn, request: Request, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    notice = Notice(title=body.title, content=body.content, status=body.status, publisher_id=current_user.id)
    if body.status == 1:
        notice.published_at = datetime.now()
    db.add(notice)
    db.flush()
    log_op(db, request, current_user, "发布", f"发布公告：{notice.title}")
    db.commit()
    return ok({"id": notice.id}, "发布成功")


@router.put("/notices/{item_id}")
def update_notice(
    item_id: int, body: NoticeIn, request: Request, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    notice = db.query(Notice).filter(Notice.id == item_id, Notice.is_deleted == 0).first()
    if notice is None:
        raise BizError(*E_NOT_FOUND)
    notice.title = body.title
    notice.content = body.content
    if notice.status == 0 and body.status == 1 and notice.published_at is None:
        notice.published_at = datetime.now()
    notice.status = body.status
    log_op(db, request, current_user, "修改", f"修改公告：{notice.title}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/notices/{item_id}")
def delete_notice(
    item_id: int, request: Request, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    notice = db.query(Notice).filter(Notice.id == item_id, Notice.is_deleted == 0).first()
    if notice is None:
        raise BizError(*E_NOT_FOUND)
    notice.is_deleted = 1
    log_op(db, request, current_user, "删除", f"删除公告：{notice.title}（软删除）")
    db.commit()
    return ok(None, "删除成功")


# ---------------- 投诉反馈 ----------------
@router.post("/feedback")
def submit_feedback(
    body: FeedbackIn,
    request: Request,
    current_user: User = Depends(require_roles("admin", "officer", "user")),
    db: Session = Depends(get_db),
):
    """提交投诉反馈（所有登录角色可提交）"""
    item = Feedback(user_id=current_user.id, title=body.title, content=body.content, status="pending")
    db.add(item)
    db.flush()
    log_op(db, request, current_user, "反馈", f"提交反馈：{body.title or body.content[:20]}")
    db.commit()
    return ok({"id": item.id}, "提交成功，等待受理")


@router.get("/feedback")
def list_feedback(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: str = Query(""),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
    db: Session = Depends(get_db),
):
    """反馈列表：管理员/交警看全部，普通用户仅看本人工单"""
    page, size = clamp_page(page, size)
    query = db.query(Feedback).filter(Feedback.is_deleted == 0)
    if _role_of(db, current_user) == "user":
        query = query.filter(Feedback.user_id == current_user.id)
    if status:
        query = query.filter(Feedback.status == status)
    total = query.count()
    rows = query.order_by(Feedback.id.desc()).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_feedback_out(f) for f in rows], "total": total, "page": page, "size": size})


def _feedback_out(f: Feedback) -> dict:
    return {
        "id": f.id,
        "user_id": f.user_id,
        "title": f.title,
        "content": f.content,
        "reply": f.reply,
        "status": f.status,
        "status_name": {"pending": "待受理", "processing": "处理中", "resolved": "已办结"}.get(f.status, f.status),
        "handler_id": f.handler_id,
        "handled_at": f.handled_at.strftime("%Y-%m-%d %H:%M:%S") if f.handled_at else None,
        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/feedback/{item_id}/handle")
def handle_feedback(
    item_id: int,
    body: FeedbackHandleIn,
    request: Request,
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """受理/处理反馈：状态 pending/processing -> processing/resolved"""
    item = db.query(Feedback).filter(Feedback.id == item_id, Feedback.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    if item.status == "resolved":
        raise BizError(*E_FEEDBACK_HANDLED)
    item.status = body.status
    item.reply = body.reply
    item.handler_id = current_user.id
    item.handled_at = datetime.now()
    log_op(db, request, current_user, "受理", f"处理反馈 #{item.id}，状态：{body.status}")
    db.commit()
    return ok(_feedback_out(item), "处理成功")
