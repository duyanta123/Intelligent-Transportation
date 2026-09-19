"""路口/信号/路况接口测试"""
import uuid

from app.core.redis_client import KEY_CAPTCHA as KEY
from app.core.redis_client import get_redis


def _new_intersection(client, admin_headers, name=None):
    name = name or f"测试路口{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/v1/intersections",
        headers=admin_headers,
        json={"name": name, "longitude": 116.40, "latitude": 39.90, "lane_count": 4, "district": "测试辖区"},
    )
    assert resp.json()["code"] == 0, resp.text
    return resp.json()["data"]["id"], name


def _new_section(client, admin_headers, start_id, end_id, lanes=2):
    name = f"测试路段{uuid.uuid4().hex[:6]}"
    resp = client.post(
        "/api/v1/road-sections",
        headers=admin_headers,
        json={
            "name": name,
            "start_intersection_id": start_id,
            "end_intersection_id": end_id,
            "lane_count": lanes,
            "length_km": 1.5,
            "direction": "东西",
        },
    )
    assert resp.json()["code"] == 0, resp.text
    return resp.json()["data"]["id"], name


class TestIntersection:
    def test_admin_create(self, client, admin_headers):
        iid, name = _new_intersection(client, admin_headers)
        rows = client.get("/api/v1/intersections", headers=admin_headers).json()["data"]
        assert any(r["id"] == iid and r["name"] == name for r in rows)

    def test_officer_can_read_but_not_create(self, client, officer_headers):
        assert client.get("/api/v1/intersections", headers=officer_headers).status_code == 200
        resp = client.post(
            "/api/v1/intersections",
            headers=officer_headers,
            json={"name": "x", "longitude": 116.4, "latitude": 39.9},
        )
        assert resp.status_code == 403

    def test_user_forbidden(self, client, user_headers):
        assert client.get("/api/v1/intersections", headers=user_headers).status_code == 403


class TestSectionAndFlow:
    def test_section_capacity_auto(self, client, admin_headers):
        iid, _ = _new_intersection(client, admin_headers)
        sid, _ = _new_section(client, admin_headers, iid, iid, lanes=3)
        rows = client.get("/api/v1/road-sections", headers=admin_headers).json()["data"]
        section = next(r for r in rows if r["id"] == sid)
        assert section["capacity"] == 3 * 600

    def test_report_flow_computes_level(self, client, admin_headers):
        iid, _ = _new_intersection(client, admin_headers)
        sid, _ = _new_section(client, admin_headers, iid, iid, lanes=2)  # capacity 1200
        resp = client.post("/api/v1/traffic-flow/report", headers=admin_headers, json={"road_section_id": sid, "flow": 12})
        data = resp.json()["data"]
        # 折算流率 720 → 饱和度 0.6 → 缓行
        assert data["flow"] == 720
        assert data["congestion_level"] == 1
        assert data["saturation"] == 0.6

    def test_report_flow_officer_allowed(self, client, officer_headers, admin_headers):
        iid, _ = _new_intersection(client, admin_headers)
        sid, _ = _new_section(client, admin_headers, iid, iid)
        resp = client.post("/api/v1/traffic-flow/report", headers=officer_headers, json={"road_section_id": sid, "flow": 1})
        assert resp.json()["code"] == 0

    def test_history_day_aggregation(self, client, admin_headers):
        iid, _ = _new_intersection(client, admin_headers)
        sid, _ = _new_section(client, admin_headers, iid, iid)
        for _ in range(3):
            client.post("/api/v1/traffic-flow/report", headers=admin_headers, json={"road_section_id": sid, "flow": 10})
        resp = client.get(
            "/api/v1/traffic-flow/history",
            headers=admin_headers,
            params={"road_section_id": sid, "granularity": "hour"},
        )
        data = resp.json()["data"]
        assert data["total"] >= 1, f"history resp: {resp.json()}"
        assert data["list"][0]["avg_flow"] == 600.0  # 10 辆/分钟 × 60

    def test_congestion_endpoint(self, client, admin_headers):
        resp = client.get("/api/v1/traffic-flow/congestion", headers=admin_headers)
        data = resp.json()["data"]
        assert "sections" in data and "intersections" in data


class TestSignal:
    def test_webster_calc_endpoint(self, client, officer_headers):
        resp = client.post(
            "/api/v1/signal-plans/calc",
            headers=officer_headers,
            json={"phases": [{"name": "南北", "flow": 800, "lanes": 2}, {"name": "东西", "flow": 1200, "lanes": 2}]},
        )
        data = resp.json()["data"]
        assert 40 <= data["cycle_seconds"] <= 180
        assert len(data["phases"]) == 2

    def test_signal_plan_crud(self, client, admin_headers):
        iid, _ = _new_intersection(client, admin_headers)
        resp = client.post(
            "/api/v1/signal-plans",
            headers=admin_headers,
            json={
                "intersection_id": iid,
                "name": "测试方案",
                "mode": "fixed",
                "cycle_seconds": 90,
                "phase_count": 2,
                "phases": [{"name": "南北", "green": 40}, {"name": "东西", "green": 40}],
                "is_active": True,
            },
        )
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/signal-plans", headers=admin_headers, params={"intersection_id": iid}).json()["data"]
        assert len(rows) == 1 and rows[0]["is_active"] == 1

    def test_signal_status_requires_login(self, client):
        assert client.get("/api/v1/signal-status").status_code == 401

    def test_captcha_key_prefix(self):
        """Redis 键前缀约定不被意外改动（回归保护）"""
        assert KEY == "captcha:{key}"
        assert get_redis() is not None
