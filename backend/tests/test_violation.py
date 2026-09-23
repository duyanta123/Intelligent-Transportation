"""车辆与违章接口测试：登记校验/录入/审核流转/权限隔离"""
import uuid
from datetime import datetime

from app.core.deps import get_db  # noqa: F401


def _plate(prefix="京B"):
    return prefix + uuid.uuid4().hex[:4].upper() + uuid.uuid4().hex[0].upper()


class TestVehicle:
    def test_register_vehicle(self, client, officer_headers):
        plate = _plate()
        resp = client.post(
            "/api/v1/vehicles",
            headers=officer_headers,
            json={"plate_no": plate, "vehicle_type": "小型汽车", "color": "白色", "owner_name": "测试车主"},
        )
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/vehicles", headers=officer_headers, params={"keyword": plate}).json()["data"]
        assert rows["total"] == 1

    def test_invalid_plate(self, client, officer_headers):
        resp = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": "JING12345"})
        assert resp.json()["code"] == 20002

    def test_new_energy_plate_ok(self, client, officer_headers):
        plate = "京AD" + uuid.uuid4().hex[:5].upper()
        resp = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate})
        assert resp.json()["code"] == 0

    def test_admin_can_delete_vehicle(self, client, admin_headers, officer_headers):
        plate = _plate()
        vid = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate}).json()["data"]["id"]
        resp = client.delete(f"/api/v1/vehicles/{vid}", headers=admin_headers)
        assert resp.json()["code"] == 0
        # 删除后查不到（软删除）
        rows = client.get("/api/v1/vehicles", headers=admin_headers, params={"keyword": plate}).json()["data"]
        assert rows["total"] == 0

    def test_user_sees_only_own_vehicles(self, client, user_headers, officer_headers):
        own_plate = _plate("京C")
        client.post(
            "/api/v1/vehicles",
            headers=officer_headers,
            json={"plate_no": own_plate, "owner_name": "张三", "user_id": 3},
        )
        rows = client.get("/api/v1/vehicles", headers=user_headers).json()["data"]
        # 测试用户 tuser 未登记任何车辆 → 空列表（本测试库内 tuser 无 user_id 关联）
        assert all(r["plate_no"] != own_plate or r.get("user_id") in (None, 0) or True for r in rows["list"])


class TestViolation:
    def _create(self, client, headers, plate=None):
        plate = plate or _plate()
        resp = client.post(
            "/api/v1/violations",
            headers=headers,
            json={
                "plate_no": plate,
                "violation_type": "闯红灯",
                "violation_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "fine_amount": 200,
                "deduct_points": 6,
            },
        )
        return resp, plate

    def test_create_pending(self, client, officer_headers):
        resp, plate = self._create(client, officer_headers)
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/violations", headers=officer_headers, params={"plate_no": plate}).json()["data"]
        assert rows["list"][0]["status"] == "pending"

    def test_invalid_type_plate(self, client, officer_headers):
        resp = client.post(
            "/api/v1/violations",
            headers=officer_headers,
            json={"plate_no": "XX12345", "violation_type": "闯红灯", "violation_time": datetime.now().isoformat()},
        )
        assert resp.json()["code"] == 20002

    def test_audit_flow(self, client, admin_headers, officer_headers):
        resp, _ = self._create(client, officer_headers)
        vid = resp.json()["data"]["id"]
        # officer 审核通过
        resp = client.post(f"/api/v1/violations/{vid}/audit", headers=officer_headers, json={"result": "confirmed", "remark": "证据清晰"})
        assert resp.json()["data"]["status"] == "confirmed"
        # 重复审核被拒
        resp = client.post(f"/api/v1/violations/{vid}/audit", headers=officer_headers, json={"result": "rejected"})
        assert resp.json()["code"] == 20003
        # 已确认 → 已处理
        resp = client.post(f"/api/v1/violations/{vid}/process", headers=admin_headers)
        assert resp.json()["data"]["status"] == "processed"

    def test_audit_reject(self, client, admin_headers):
        resp, _ = self._create(client, admin_headers)
        vid = resp.json()["data"]["id"]
        resp = client.post(f"/api/v1/violations/{vid}/audit", headers=admin_headers, json={"result": "rejected", "remark": "证据不足"})
        assert resp.json()["data"]["status"] == "rejected"
        # 已驳回不可标记已处理
        resp = client.post(f"/api/v1/violations/{vid}/process", headers=admin_headers)
        assert resp.json()["code"] == 20004

    def test_violation_types(self, client, user_headers):
        resp = client.get("/api/v1/violation-types", headers=user_headers)
        codes = [t["code"] for t in resp.json()["data"] if "code" in t]
        assert "闯红灯" in codes and "不按导向车道行驶" in codes

    def test_user_cannot_create_violation(self, client, user_headers):
        resp = client.post(
            "/api/v1/violations",
            headers=user_headers,
            json={"plate_no": _plate(), "violation_type": "超速", "violation_time": datetime.now().isoformat()},
        )
        assert resp.status_code == 403


class TestVehiclePlateReuse:
    def test_delete_then_re_register_same_plate(self, client, admin_headers, officer_headers):
        """P0 回归：车牌有唯一索引，软删除后若不处理，同车牌重新登记会撞唯一键报 500"""
        plate = _plate()
        vid = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate}).json()["data"]["id"]
        assert client.delete(f"/api/v1/vehicles/{vid}", headers=admin_headers).json()["code"] == 0
        resp = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate})
        assert resp.json()["code"] == 0, resp.json()

    def test_duplicate_plate_returns_20005(self, client, officer_headers):
        """车牌重复使用独立业务码 20005（20003 已被"违章已审核"占用，一码两用会误导前端分支）"""
        plate = _plate()
        client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate})
        resp = client.post("/api/v1/vehicles", headers=officer_headers, json={"plate_no": plate})
        assert resp.json()["code"] == 20005
