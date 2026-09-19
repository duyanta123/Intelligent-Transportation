"""认证辅助：角色查询、菜单树构建"""
from sqlalchemy.orm import Session

from app.models import Menu, Role, RoleMenu, UserRole


def get_user_role_code(db: Session, user) -> str:
    """查询用户主角色编码（一人一角色）"""
    row = (
        db.query(Role.code)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id, UserRole.is_deleted == 0, Role.is_deleted == 0)
        .first()
    )
    return row[0] if row else "user"


def get_role_menu_list(db: Session, role_id: int) -> list[Menu]:
    """角色可见菜单（平铺、按排序号）"""
    return (
        db.query(Menu)
        .join(RoleMenu, RoleMenu.menu_id == Menu.id)
        .filter(RoleMenu.role_id == role_id, RoleMenu.is_deleted == 0, Menu.is_deleted == 0)
        .order_by(Menu.sort_order)
        .all()
    )


def build_menu_tree(menus: list[Menu], parent_id: int = 0) -> list[dict]:
    """把平铺菜单组装成树形结构（同级按 sort_order、id 排序，不依赖调用方传入顺序）"""
    items = sorted(
        (m for m in menus if m.parent_id == parent_id),
        key=lambda m: (m.sort_order, m.id),
    )
    tree = []
    for m in items:
        node = {
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
        children = build_menu_tree(menus, m.id)
        if children:
            node["children"] = children
        tree.append(node)
    return tree


def get_user_menus(db: Session, user) -> list[dict]:
    """当前用户角色可见的菜单树"""

    role = db.query(Role).join(UserRole, UserRole.role_id == Role.id).filter(
        UserRole.user_id == user.id, UserRole.is_deleted == 0, Role.is_deleted == 0
    ).first()
    if role is None:
        return []
    menus = get_role_menu_list(db, role.id)
    return build_menu_tree(menus)
