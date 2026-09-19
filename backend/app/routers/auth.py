"""认证授权路由：验证码/注册/登录/登出/改密/个人信息"""
import time
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.redis_client import (
    KEY_CAPTCHA,
    KEY_LOGIN_FAIL,
    KEY_LOGIN_LOCK,
    KEY_TOKEN_BLACKLIST,
    get_redis,
)
from app.core.response import (
    E_CAPTCHA_WRONG,
    E_LOGIN_FAILED,
    E_LOGIN_LOCKED,
    E_OLD_PASSWORD,
    E_USER_DISABLED,
    E_USER_EXISTS,
    BizError,
    ok,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import LoginIn, PasswordIn, ProfileUpdateIn, RegisterIn
from app.services.auth_service import get_user_menus, get_user_role_code
from app.services.oplog import log_op
from app.utils.captcha import generate_captcha

router = APIRouter(prefix="/auth", tags=["认证授权"])

# 登录限流：连续失败 5 次锁定 10 分钟（附录 4.1）
FAIL_LIMIT = 5
LOCK_SECONDS = 600


@router.get("/captcha")
def get_captcha():
    """图形验证码：code 存 Redis，TTL 默认 300 秒"""
    code, image = generate_captcha()
    key = uuid.uuid4().hex
    redis = get_redis()
    redis.setex(KEY_CAPTCHA.format(key=key), settings.CAPTCHA_TTL_SECONDS, code.upper())
    return ok({"key": key, "image": image}, "获取验证码成功")


def _check_login_lock(redis, username: str, ip: str) -> None:
    if redis.exists(KEY_LOGIN_LOCK.format(name=username)) or redis.exists(KEY_LOGIN_LOCK.format(name=f"ip:{ip}")):
        raise BizError(*E_LOGIN_LOCKED)


def _record_login_fail(redis, username: str, ip: str) -> None:
    """失败计数 +1；达到 5 次立即锁定 10 分钟（本次请求即返回锁定响应）"""
    for name in (username, f"ip:{ip}"):
        fail_key = KEY_LOGIN_FAIL.format(name=name)
        count = redis.incr(fail_key)
        if count == 1:
            redis.expire(fail_key, LOCK_SECONDS)
        if count >= FAIL_LIMIT:
            redis.setex(KEY_LOGIN_LOCK.format(name=name), LOCK_SECONDS, "1")
            redis.delete(fail_key)
            raise BizError(*E_LOGIN_LOCKED)


@router.post("/register")
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.username == body.username, User.is_deleted == 0).first()
    if exists:
        raise BizError(*E_USER_EXISTS)
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        real_name=body.real_name or body.username,
        phone=body.phone,
        email="",
        status=1,
    )
    db.add(user)
    db.flush()
    # 默认授予普通用户角色（role 表 code=user）
    from app.models import Role, UserRole

    role = db.query(Role).filter(Role.code == "user", Role.is_deleted == 0).first()
    if role:
        db.add(UserRole(user_id=user.id, role_id=role.id))
    log_op(db, request, user, "注册", f"新用户注册：{body.username}")
    db.commit()
    return ok({"id": user.id, "username": user.username}, "注册成功")


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    redis = get_redis()
    ip = request.client.host if request.client else ""
    _check_login_lock(redis, body.username, ip)

    # 1. 校验图形验证码（一次性：校验后立即删除）
    captcha_key = KEY_CAPTCHA.format(key=body.captcha_key)
    stored = redis.get(captcha_key)
    redis.delete(captcha_key)
    if not stored or stored.upper() != body.captcha_code.strip().upper():
        raise BizError(*E_CAPTCHA_WRONG)

    # 2. 校验账号密码
    user = db.query(User).filter(User.username == body.username, User.is_deleted == 0).first()
    if user is None or not verify_password(body.password, user.password_hash):
        # 计数达到 5 次时内部直接抛锁定异常（429）
        _record_login_fail(redis, body.username, ip)
        raise BizError(*E_LOGIN_FAILED)
    if user.status != 1:
        raise BizError(*E_USER_DISABLED)

    # 3. 登录成功：清除失败计数，签发 JWT
    redis.delete(KEY_LOGIN_FAIL.format(name=body.username))
    redis.delete(KEY_LOGIN_FAIL.format(name=f"ip:{ip}"))
    role = get_user_role_code(db, user)
    token = create_access_token(user.id, user.username, role)
    log_op(db, request, user, "登录", f"用户 {user.username} 登录成功")
    db.commit()
    return ok(
        {
            "token": token,
            "expires_in": settings.JWT_EXPIRE_MINUTES * 60,
            "role": role,
            "user": {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "phone": user.phone,
                "email": user.email,
            },
            "menus": get_user_menus(db, user),
        },
        "登录成功",
    )


@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """登出：当前 token 加入 Redis 黑名单，TTL=剩余有效期"""
    token = getattr(request.state, "token", "")
    if token:
        from app.core.security import decode_access_token

        payload = decode_access_token(token)
        if payload and payload.get("exp"):
            remaining = int(payload["exp"] - time.time())
            if remaining > 0:
                get_redis().setex(KEY_TOKEN_BLACKLIST.format(token=token), remaining, "1")
    log_op(db, request, current_user, "登出", f"用户 {current_user.username} 退出登录")
    db.commit()
    return ok(None, "已退出登录")


@router.put("/password")
def change_password(
    body: PasswordIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise BizError(*E_OLD_PASSWORD)
    current_user.password_hash = hash_password(body.new_password)
    log_op(db, request, current_user, "改密", f"用户 {current_user.username} 修改了登录密码")
    db.commit()
    return ok(None, "密码修改成功，请重新登录")


@router.get("/profile")
def profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = get_user_role_code(db, current_user)
    return ok(
        {
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "phone": current_user.phone,
            "email": current_user.email,
            "role": role,
            "menus": get_user_menus(db, current_user),
        }
    )


@router.put("/profile")
def update_profile(
    body: ProfileUpdateIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """自助修改个人资料（姓名/手机/邮箱），所有登录角色可用"""
    for field in ("real_name", "phone", "email"):
        value = getattr(body, field)
        if value is not None:
            setattr(current_user, field, value)
    log_op(db, request, current_user, "修改", f"用户 {current_user.username} 更新了个人资料")
    db.commit()
    return ok(
        {
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "phone": current_user.phone,
            "email": current_user.email,
        },
        "资料已更新",
    )
