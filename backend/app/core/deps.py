"""依赖项：数据库会话、当前登录用户、角色鉴权"""
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.redis_client import KEY_TOKEN_BLACKLIST, get_redis
from app.core.response import E_FORBIDDEN, E_UNAUTHORIZED, BizError
from app.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """解析 Authorization: Bearer <token>，校验黑名单与用户状态"""
    from app.models import User  # 局部导入避免循环依赖

    if credentials is None:
        raise BizError(*E_UNAUTHORIZED)
    token = credentials.credentials
    redis = get_redis()
    if redis.exists(KEY_TOKEN_BLACKLIST.format(token=token)):
        raise BizError(10001, "登录已失效，请重新登录", 401)
    payload = decode_access_token(token)
    if payload is None:
        raise BizError(10001, "登录已过期，请重新登录", 401)
    user = db.get(User, int(payload["sub"]))
    if user is None or user.is_deleted or user.status != 1:
        raise BizError(10001, "账号不存在或已被禁用", 401)
    # 把 token 与角色挂到 request.state，供登出/操作日志使用
    request.state.token = token
    request.state.role = payload.get("role", "")
    return user


def require_roles(*role_codes: str):
    """角色鉴权工厂：require_roles('admin') / require_roles('admin', 'officer')"""

    def checker(request: Request, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        from app.services.auth_service import get_user_role_code

        role = get_user_role_code(db, current_user)
        if role not in role_codes:
            raise BizError(*E_FORBIDDEN)
        request.state.role = role
        return current_user

    return checker
