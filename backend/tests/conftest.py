"""pytest 全局夹具：独立测试库 smart_traffic_test，禁止打正式库

约定：
  - TESTING=1：禁用 APScheduler 模拟任务
  - REDIS_DB=15：测试专用 Redis 库，避免污染业务缓存
  - 测试库会话级自动建表/清表（含建库与删库）
"""
import os

# 必须在导入 app 之前设置环境变量
os.environ["TESTING"] = "1"
os.environ["MOCK_DATA_ENABLED"] = "false"
os.environ["REDIS_DB"] = "15"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base
from app.core.redis_client import KEY_CAPTCHA, get_redis
from app.core.security import hash_password
from app.models import Menu, Role, RoleMenu, User, UserRole


@pytest.fixture(scope="session")
def test_engine():
    """会话级：创建独立测试库并建表，结束后删库"""
    admin_engine = create_engine(settings.server_db_url)
    with admin_engine.connect() as conn:
        conn.execute(
            text(
                f"CREATE DATABASE IF NOT EXISTS {settings.test_db_name} "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci"
            )
        )
        conn.commit()
    engine = create_engine(settings.test_db_url)
    Base.metadata.create_all(engine)
    # 清空测试专用 Redis 库
    get_redis().flushdb()
    yield engine
    Base.metadata.drop_all(engine)
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {settings.test_db_name}"))
        conn.commit()
    admin_engine.dispose()
    engine.dispose()


@pytest.fixture(scope="session")
def seed_data(test_engine):
    """会话级种子：三个测试账号（admin/officer/user 角色）与最小菜单集"""
    factory = sessionmaker(bind=test_engine)
    s = factory()
    for code, name in [("admin", "管理员"), ("officer", "交警"), ("user", "普通用户")]:
        s.add(Role(code=code, name=name, description=""))
    s.flush()
    users = {}
    for username, role_code in [("tadmin", "admin"), ("tofficer", "officer"), ("tuser", "user")]:
        user = User(username=username, password_hash=hash_password("123456"), real_name=username, status=1)
        s.add(user)
        s.flush()
        role = s.query(Role).filter(Role.code == role_code).first()
        s.add(UserRole(user_id=user.id, role_id=role.id))
        users[role_code] = user

    # 最小菜单集：id 固定，便于断言
    menus = [
        Menu(id=1, parent_id=0, name="系统仪表盘", path="/dashboard", menu_type=1, sort_order=1),
        Menu(id=2, parent_id=0, name="数据可视化大屏", path="/big-screen", menu_type=1, sort_order=2),
        Menu(id=3, parent_id=0, name="交通管理", menu_type=0, sort_order=10),
        Menu(id=4, parent_id=3, name="路口管理", path="/traffic/intersections", menu_type=1, sort_order=11),
        Menu(id=5, parent_id=3, name="信号配时", path="/traffic/signal-plans", menu_type=1, sort_order=12),
        Menu(id=6, parent_id=0, name="公共服务", menu_type=0, sort_order=60),
        Menu(id=7, parent_id=6, name="公告资讯", path="/service/notices", menu_type=1, sort_order=61),
    ]
    for m in menus:
        s.add(m)
    s.flush()
    grants = {
        "admin": [1, 2, 3, 4, 5, 6, 7],
        "officer": [1, 2, 3, 4, 5, 6, 7],
        "user": [2, 6, 7],
    }
    for role_code, menu_ids in grants.items():
        role = s.query(Role).filter(Role.code == role_code).first()
        for mid in menu_ids:
            s.add(RoleMenu(role_id=role.id, menu_id=mid))
    s.commit()
    s.close()
    return users


@pytest.fixture()
def db_session(test_engine, seed_data):
    """函数级测试会话：与 client 的依赖注入共享同一会话（避免事务快照不一致）"""
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    """TestClient：get_db 依赖指向测试库会话"""
    from app.core.deps import get_db
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def login_as(client):
    """登录辅助：返回 Authorization 头"""

    def _login(username: str) -> dict:
        captcha = client.get("/api/v1/auth/captcha").json()["data"]
        code = get_redis().get(KEY_CAPTCHA.format(key=captcha["key"]))
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "username": username,
                "password": "123456",
                "captcha_key": captcha["key"],
                "captcha_code": code,
            },
        )
        body = resp.json()
        assert body["code"] == 0, f"登录失败：{body}"
        return {"Authorization": f"Bearer {body['data']['token']}"}

    return _login


@pytest.fixture()
def admin_headers(login_as):
    return login_as("tadmin")


@pytest.fixture()
def officer_headers(login_as):
    return login_as("tofficer")


@pytest.fixture()
def user_headers(login_as):
    return login_as("tuser")
