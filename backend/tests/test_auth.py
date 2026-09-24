"""认证授权接口测试：验证码/注册/登录/限流锁定/登出黑名单/改密"""
import uuid

from app.core.redis_client import get_redis


def _captcha_code(client) -> tuple[str, str]:
    data = client.get("/api/v1/auth/captcha").json()["data"]
    code = get_redis().get(f"captcha:{data['key']}")
    return data["key"], code


def _do_login(client, username: str, password: str):
    key, code = _captcha_code(client)
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, "captcha_key": key, "captcha_code": code or "XXXX"},
    )


def test_captcha_stored_in_redis(client):
    data = client.get("/api/v1/auth/captcha").json()["data"]
    assert data["image"].startswith("data:image/png;base64,")
    stored = get_redis().get(f"captcha:{data['key']}")
    assert stored is not None and len(stored) == 4


def test_login_wrong_captcha(client):
    key, _ = _captcha_code(client)
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "tadmin", "password": "123456", "captcha_key": key, "captcha_code": "WRONG"},
    )
    assert resp.json()["code"] == 10004


def test_login_wrong_password(client):
    resp = _do_login(client, "tadmin", "bad-password")
    assert resp.status_code == 401
    assert resp.json()["code"] == 10002


def test_login_success_returns_token_and_menus(client):
    resp = _do_login(client, "tadmin", "123456")
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["role"] == "admin"
    assert body["data"]["token"].count(".") == 2
    assert any(m["name"] == "系统仪表盘" for m in body["data"]["menus"])


def test_profile_requires_token(client):
    resp = client.get("/api/v1/auth/profile")
    assert resp.status_code == 401


def test_profile_with_token(client, admin_headers):
    resp = client.get("/api/v1/auth/profile", headers=admin_headers)
    assert resp.json()["data"]["username"] == "tadmin"


def test_register_and_login(client):
    username = f"u{uuid.uuid4().hex[:8]}"
    resp = client.post("/api/v1/auth/register", json={"username": username, "password": "abc12345"})
    assert resp.json()["code"] == 0
    resp = _do_login(client, username, "abc12345")
    assert resp.json()["data"]["role"] == "user"


def test_register_duplicate_rejected(client):
    resp = client.post("/api/v1/auth/register", json={"username": "tadmin", "password": "abc12345"})
    assert resp.json()["code"] == 10006


def test_logout_blacklists_token(client, admin_headers):
    token = admin_headers["Authorization"].split(" ")[1]
    resp = client.post("/api/v1/auth/logout", headers=admin_headers)
    assert resp.json()["code"] == 0
    assert get_redis().exists(f"token:blacklist:{token}")
    after = client.get("/api/v1/auth/profile", headers=admin_headers)
    assert after.status_code == 401


def test_change_password_wrong_old(client, admin_headers):
    resp = client.put(
        "/api/v1/auth/password", headers=admin_headers, json={"old_password": "wrong", "new_password": "new123456"}
    )
    assert resp.json()["code"] == 10008


def test_change_password_then_relogin(client):
    username = f"cp{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/auth/register", json={"username": username, "password": "abc12345"})
    headers = None
    resp = _do_login(client, username, "abc12345")
    headers = {"Authorization": f"Bearer {resp.json()['data']['token']}"}
    resp = client.put(
        "/api/v1/auth/password", headers=headers, json={"old_password": "abc12345", "new_password": "xyz987654"}
    )
    assert resp.json()["code"] == 0
    assert _do_login(client, username, "abc12345").status_code == 401
    assert _do_login(client, username, "xyz987654").json()["code"] == 0


def test_login_lockout_after_5_failures(client):
    """连续失败 5 次锁定 10 分钟；锁定期间正确密码也拒绝；结束后清理锁避免污染其他用例"""
    username = f"lk{uuid.uuid4().hex[:8]}"
    client.post("/api/v1/auth/register", json={"username": username, "password": "abc12345"})
    try:
        for _ in range(5):
            key, code = _captcha_code(client)
            resp = client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": "wrong", "captcha_key": key, "captcha_code": code},
            )
        last = resp.json()
        assert resp.status_code == 429 and last["code"] == 10005, last
        # 锁定期内正确密码也被拒绝
        resp = _do_login(client, username, "abc12345")
        assert resp.status_code == 429
    finally:
        # 无论断言成败都清理锁与计数，避免影响同 IP 的其他用例
        redis = get_redis()
        for k in redis.keys("login:lock:*") + redis.keys("login:fail:*"):
            redis.delete(k)


def test_update_profile_self_service(client, admin_headers):
    """自助资料修改：所有角色可改自己的姓名/手机/邮箱"""
    resp = client.put(
        "/api/v1/auth/profile",
        headers=admin_headers,
        json={"real_name": "新名字", "phone": "13900009999", "email": "me@traffic.local"},
    )
    body = resp.json()
    assert body["code"] == 0, body
    assert body["data"]["real_name"] == "新名字"
    # profile 回读一致
    prof = client.get("/api/v1/auth/profile", headers=admin_headers).json()["data"]
    assert prof["real_name"] == "新名字" and prof["email"] == "me@traffic.local"


def test_captcha_single_use(client):
    """验证码原子取出即销毁：同一验证码第二次使用必须失败（防并发重放）"""
    key, code = _captcha_code(client)
    payload = {"username": "tadmin", "password": "123456", "captcha_key": key, "captcha_code": code}
    assert client.post("/api/v1/auth/login", json=payload).json()["code"] == 0
    resp = client.post("/api/v1/auth/login", json=payload)
    assert resp.json()["code"] == 10004


def test_password_change_revokes_existing_tokens(client, login_as):
    """改密后旧 token 必须失效（iat 早于改密时间下限），新登录不受影响"""
    import time

    headers = login_as("tofficer")
    time.sleep(1.1)  # 与 token 签发时间错开 1 秒（JWT iat 秒级精度）
    resp = client.put("/api/v1/auth/password", headers=headers, json={"old_password": "123456", "new_password": "abc12345"})
    assert resp.json()["code"] == 0
    # 旧 token 已被吊销
    assert client.get("/api/v1/auth/profile", headers=headers).status_code == 401
    # 新密码可登录、新 token 可用
    resp_login = _do_login(client, "tofficer", "abc12345")
    assert resp_login.json()["code"] == 0
    new_headers = {"Authorization": f"Bearer {resp_login.json()['data']['token']}"}
    assert client.get("/api/v1/auth/profile", headers=new_headers).status_code == 200
    # 改回原密码，避免影响其他用例（种子账号密码约定 123456）
    revert = client.put(
        "/api/v1/auth/password",
        headers=new_headers,
        json={"old_password": "abc12345", "new_password": "123456"},
    )
    assert revert.json()["code"] == 0
