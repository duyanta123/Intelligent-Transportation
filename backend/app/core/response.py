"""统一响应结构 {code, message, data} 与业务异常

code 约定（附录 E.2）：
  0 成功；1xxxx 用户与权限；2xxxx 交通业务；3xxxx 停车与计费；4xxxx 公共服务；9xxxx 系统错误
HTTP 状态码照常表达 401/403/404/422/500
"""
from typing import Any


def ok(data: Any = None, message: str = "操作成功") -> dict:
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data}


class BizError(Exception):
    """业务异常：路由/服务层抛出，由全局异常处理器转成统一响应"""

    def __init__(self, code: int, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


# ---- 用户与权限 1xxxx ----
E_UNAUTHORIZED = (10001, "未登录或登录已过期，请重新登录", 401)
E_FORBIDDEN = (10003, "没有操作权限", 403)
E_LOGIN_FAILED = (10002, "用户名或密码错误", 401)
E_CAPTCHA_WRONG = (10004, "验证码错误或已过期", 400)
E_LOGIN_LOCKED = (10005, "连续失败次数过多，账号已锁定 10 分钟", 429)
E_USER_EXISTS = (10006, "用户名已存在", 400)
E_USER_DISABLED = (10007, "账号已被禁用", 403)
E_OLD_PASSWORD = (10008, "原密码不正确", 400)

# ---- 交通业务 2xxxx ----
E_NOT_FOUND = (20001, "记录不存在", 404)
E_PLATE_INVALID = (20002, "车牌号格式不正确", 400)
E_VIOLATION_AUDITED = (20003, "该违章已审核，不能重复审核", 400)
E_VIOLATION_PROCESS_DENIED = (20004, "仅审核通过的违章可标记为已处理", 400)
E_PLATE_DUPLICATE = (20005, "该车牌号已登记", 400)
E_SIGNAL_INFEASIBLE = (20006, "配时方案不可行：相位过多或最短绿灯之和已超出最大周期", 400)

# ---- 停车与计费 3xxxx ----
E_PARKING_FULL = (30001, "停车场车位已满", 400)
E_PARKING_DUP = (30002, "该车牌已在场内，请勿重复入场", 400)
E_PARKING_NO_RECORD = (30003, "未找到该车牌的在场记录", 404)

# ---- 公共服务 4xxxx ----
E_FEEDBACK_HANDLED = (40001, "该反馈已办结，不能再次处理", 400)

# ---- 系统错误 9xxxx ----
E_SYSTEM = (90000, "系统繁忙，请稍后重试", 500)
E_VALIDATION = (90001, "请求参数校验失败", 422)
E_UPLOAD = (90002, "文件上传失败：仅支持 jpg/png/webp 且不超过 5MB", 400)
E_LPR_FAILED = (90003, "车牌识别失败，请手动录入车牌", 503)
