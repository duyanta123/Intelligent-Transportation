"""Redis 客户端（仅使用 Redis 5 支持的命令）"""
import redis

from app.core.config import settings

_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    protocol=2,  # 本机 Redis 5.0.14 不支持 RESP3（HELLO 命令），强制 RESP2
)


def get_redis() -> "redis.Redis":
    return redis.Redis(connection_pool=_pool)


# 键名约定（集中在此处，避免散落各处）
KEY_CAPTCHA = "captcha:{key}"            # 图形验证码，TTL=CAPTCHA_TTL_SECONDS
KEY_TOKEN_BLACKLIST = "token:blacklist:{token}"  # 登出 token 黑名单，TTL=剩余有效期
KEY_LOGIN_FAIL = "login:fail:{name}"     # 登录失败计数（账号/IP），TTL=10 分钟
KEY_LOGIN_LOCK = "login:lock:{name}"     # 登录锁定标记，TTL=10 分钟
KEY_DASHBOARD = "dashboard:realtime"     # 大屏聚合缓存，TTL=8 秒
