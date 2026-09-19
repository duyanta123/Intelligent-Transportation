"""FastAPI 入口：智慧交通综合管理服务平台"""
import logging
import os
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.response import E_SYSTEM, E_VALIDATION, BizError, fail, ok

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="智慧交通综合管理服务平台 API",
    description="软件工程课程作业：Vue3 + FastAPI + MySQL + Redis 单体三层架构",
    version="1.0.0",
    docs_url="/docs",
)

# 前端开发服务器跨域（5173）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- 统一异常处理：所有错误都返回 {code, message, data} ----
@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError):
    return JSONResponse(status_code=exc.http_status, content=fail(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(x) for x in first.get("loc", [])[1:]) or "参数"
    msg = f"{field} 校验失败：{first.get('msg', '')}"
    return JSONResponse(status_code=422, content=fail(E_VALIDATION[0], msg))


@app.exception_handler(Exception)
async def system_error_handler(request: Request, exc: Exception):
    logging.getLogger("smart-traffic").exception("未捕获异常：%s", exc)
    return JSONResponse(status_code=500, content=fail(*E_SYSTEM))


# ---- 上传目录静态回显：/static/uploads/<file> ----
upload_dir = os.path.join(settings.UPLOAD_DIR)
os.makedirs(upload_dir, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=upload_dir), name="uploads")

# ---- 路由注册：统一前缀 /api/v1 ----
from app.routers import (
    admin,
    auth,
    dashboard,
    lpr,
    parking,
    service,
    signal,
    system,
    traffic,
    violation,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(signal.router, prefix="/api/v1")
app.include_router(traffic.router, prefix="/api/v1")
app.include_router(violation.router, prefix="/api/v1")
app.include_router(parking.router, prefix="/api/v1")
app.include_router(lpr.router, prefix="/api/v1")
app.include_router(service.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["系统"])
def health():
    """健康检查（部署监控/验收用）"""
    return ok({"status": "up", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})


@app.on_event("startup")
def on_startup():
    # 测试环境下不启动定时任务与模型预热
    if not settings.TESTING:
        from app.tasks.scheduler import start_scheduler

        start_scheduler()
        # 后台预热车牌识别模型（首次运行自动下载约 12MB，不阻塞启动）
        from app.services.lpr_service import preload_async

        preload_async()


@app.on_event("shutdown")
def on_shutdown():
    from app.tasks.scheduler import stop_scheduler

    stop_scheduler()
