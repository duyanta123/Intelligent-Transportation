"""公共服务与大屏接口测试：公告/反馈/大屏缓存/管理仪表盘"""
import uuid

from app.core.redis_client import get_redis


class TestNotice:
    def test_admin_publish(self, client, admin_headers):
        title = f"测试公告{uuid.uuid4().hex[:6]}"
        resp = client.post("/api/v1/notices", headers=admin_headers, json={"title": title, "content": "内容", "status": 1})
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/notices", headers=admin_headers).json()["data"]
        assert any(r["title"] == title for r in rows["list"])

    def test_user_cannot_publish(self, client, user_headers):
        resp = client.post("/api/v1/notices", headers=user_headers, json={"title": "x", "content": "y"})
        assert resp.status_code == 403

    def test_user_sees_published_only(self, client, admin_headers, user_headers):
        draft = f"草稿{uuid.uuid4().hex[:6]}"
        client.post("/api/v1/notices", headers=admin_headers, json={"title": draft, "content": "", "status": 0})
        titles = [r["title"] for r in client.get("/api/v1/notices", headers=user_headers).json()["data"]["list"]]
        assert draft not in titles


class TestFeedback:
    def test_user_submit_and_track(self, client, user_headers):
        content = f"测试反馈内容{uuid.uuid4().hex}"
        resp = client.post("/api/v1/feedback", headers=user_headers, json={"title": "问题反馈", "content": content})
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/feedback", headers=user_headers).json()["data"]
        assert any(r["content"] == content and r["status"] == "pending" for r in rows["list"])

    def test_officer_handle_flow(self, client, officer_headers, user_headers):
        content = f"待处理{uuid.uuid4().hex}"
        fid = client.post("/api/v1/feedback", headers=user_headers, json={"title": "t", "content": content}).json()["data"]["id"]
        resp = client.post(
            f"/api/v1/feedback/{fid}/handle", headers=officer_headers, json={"status": "processing", "reply": "正在核实"}
        )
        assert resp.json()["data"]["status"] == "processing"
        resp = client.post(
            f"/api/v1/feedback/{fid}/handle", headers=officer_headers, json={"status": "resolved", "reply": "已解决"}
        )
        assert resp.json()["data"]["status"] == "resolved"

    def test_resolved_cannot_rehandle(self, client, officer_headers, user_headers):
        fid = client.post(
            "/api/v1/feedback", headers=user_headers, json={"title": "t2", "content": f"已办结{uuid.uuid4().hex}"}
        ).json()["data"]["id"]
        client.post(f"/api/v1/feedback/{fid}/handle", headers=officer_headers, json={"status": "resolved", "reply": "完成"})
        resp = client.post(f"/api/v1/feedback/{fid}/handle", headers=officer_headers, json={"status": "processing", "reply": "再开"})
        assert resp.json()["code"] == 40001

    def test_user_cannot_handle(self, client, user_headers):
        fid = client.post(
            "/api/v1/feedback", headers=user_headers, json={"title": "t3", "content": f"内容{uuid.uuid4().hex}"}
        ).json()["data"]["id"]
        resp = client.post(f"/api/v1/feedback/{fid}/handle", headers=user_headers, json={"status": "resolved", "reply": "x"})
        assert resp.status_code == 403


class TestDashboard:
    def test_realtime_structure(self, client, user_headers):
        resp = client.get("/api/v1/dashboard/realtime", headers=user_headers)
        data = resp.json()["data"]
        for key in ("flow_trend", "map_points", "signal_dist", "violation_top", "parking", "kpi"):
            assert key in data
        assert "today_flow" in data["kpi"]

    def test_realtime_redis_cache(self, client, user_headers):
        """大屏聚合走 Redis 缓存（TTL 8 秒）：第二次请求应命中缓存键"""
        redis = get_redis()
        redis.delete("dashboard:realtime")
        client.get("/api/v1/dashboard/realtime", headers=user_headers)
        first = redis.get("dashboard:realtime")
        assert first is not None
        ttl = redis.ttl("dashboard:realtime")
        assert 0 < ttl <= 8
        second = client.get("/api/v1/dashboard/realtime", headers=user_headers).json()["data"]
        import json

        assert json.loads(first) == second

    def test_summary_officer_allowed_user_forbidden(self, client, officer_headers, user_headers):
        assert client.get("/api/v1/dashboard/summary", headers=officer_headers).status_code == 200
        assert client.get("/api/v1/dashboard/summary", headers=user_headers).status_code == 403


class TestAdminStats:
    def test_stats(self, client, admin_headers):
        resp = client.get("/api/v1/admin/stats", headers=admin_headers)
        data = resp.json()["data"]
        assert data["user_count"] >= 3
        assert "parking_rate" in data

    def test_recent_logs(self, client, admin_headers):
        # 前面的登录/操作应已产生日志
        resp = client.get("/api/v1/admin/recent-logs", headers=admin_headers, params={"limit": 5})
        rows = resp.json()["data"]
        assert 1 <= len(rows) <= 5

    def test_user_forbidden_on_admin_stats(self, client, user_headers):
        assert client.get("/api/v1/admin/stats", headers=user_headers).status_code == 403
