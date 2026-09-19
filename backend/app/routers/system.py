"""用户/角色/菜单/操作日志（管理端，admin）"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import E_NOT_FOUND, BizError, ok
from app.models import Menu, OpLog, Role, User
from app.schemas import MenuIn, UserUpdateIn
from app.services.oplog import log_op
from app.utils.validators import clamp_page

router = APIRouter(tags=["用户权限"])


@router.get("/users")
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str = Query("", description="用户名/姓名/手机号"),
    admin_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    page, size = clamp_page(page, size)
    query = db.query(User).filter(User.is_deleted == 0)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(User.username.like(like), User.real_name.like(like), User.phone.like(like))
        )
    total = query.count()
    rows = query.order_by(User.id).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_user_out(u) for u in rows], "total": total, "page": page, "size": size})


def _user_out(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "real_name": u.real_name,
        "phone": u.phone,
        "email": u.email,
        "status": u.status,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdateIn,
    request: Request,
    admin_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == 0).first()
    if user is None:
        raise BizError(*E_NOT_FOUND)
    for field in ("real_name", "phone", "email", "status"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    log_op(db, request, user, "修改", f"管理员更新用户信息：{user.username}")
    db.commit()
    return ok(_user_out(user), "更新成功")


@router.get("/roles")
def list_roles(admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    rows = db.query(Role).filter(Role.is_deleted == 0).order_by(Role.id).all()
    return ok([{"id": r.id, "code": r.code, "name": r.name, "description": r.description} for r in rows])


# ---------------- 菜单 CRUD ----------------
@router.get("/menus")
def list_menus(admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    rows = db.query(Menu).filter(Menu.is_deleted == 0).order_by(Menu.sort_order, Menu.id).all()
    return ok(
        [
            {
                "id": m.id,
                "parent_id": m.parent_id,
                "name": m.name,
                "path": m.path,
                "component": m.component,
                "icon": m.icon,
                "menu_type": m.menu_type,
                "sort_order": m.sort_order,
                "visible": m.visible,
            }
            for m in rows
        ]
    )


@router.post("/menus")
def create_menu(body: MenuIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    menu = Menu(**body.model_dump())
    db.add(menu)
    db.flush()
    log_op(db, request, admin_user, "新增", f"新增菜单：{menu.name}")
    db.commit()
    return ok({"id": menu.id}, "创建成功")


@router.put("/menus/{menu_id}")
def update_menu(
    menu_id: int, body: MenuIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.is_deleted == 0).first()
    if menu is None:
        raise BizError(*E_NOT_FOUND)
    for field, value in body.model_dump().items():
        setattr(menu, field, value)
    log_op(db, request, admin_user, "修改", f"修改菜单：{menu.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/menus/{menu_id}")
def delete_menu(menu_id: int, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)):
    menu = db.query(Menu).filter(Menu.id == menu_id, Menu.is_deleted == 0).first()
    if menu is None:
        raise BizError(*E_NOT_FOUND)
    menu.is_deleted = 1
    log_op(db, request, admin_user, "删除", f"删除菜单：{menu.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


@router.get("/op-logs")
def list_op_logs(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    username: str = Query(""),
    action: str = Query(""),
    admin_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    page, size = clamp_page(page, size)
    query = db.query(OpLog).filter(OpLog.is_deleted == 0)
    if username:
        query = query.filter(OpLog.username.like(f"%{username}%"))
    if action:
        query = query.filter(OpLog.action == action)
    total = query.count()
    rows = query.order_by(OpLog.id.desc()).offset((page - 1) * size).limit(size).all()
    return ok(
        {
            "list": [
                {
                    "id": r.id,
                    "username": r.username,
                    "action": r.action,
                    "detail": r.detail,
                    "ip": r.ip,
                    "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "size": size,
        }
    )
