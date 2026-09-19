"""智慧停车接口测试：计费规则/出入场/结算/权限"""
import uuid


def _plate():
    """生成合规 7 位测试车牌（京A + 5 位字母数字）"""
    return "京A" + uuid.uuid4().hex[:4].upper() + uuid.uuid4().hex[0].upper()


def _new_lot(client, admin_headers, total=100, with_rule=False):
    rule_id = None
    if with_rule:
        resp = client.post(
            "/api/v1/fee-rules",
            headers=admin_headers,
            json={"name": f"测试规则{uuid.uuid4().hex[:4]}", "free_minutes": 15, "first_hour_fee": 5, "hourly_fee": 3, "daily_cap": 40},
        )
        rule_id = resp.json()["data"]["id"]
    resp = client.post(
        "/api/v1/parking-lots",
        headers=admin_headers,
        json={"name": f"测试停车场{uuid.uuid4().hex[:6]}", "address": "测试地址", "total_slots": total, "fee_rule_id": rule_id},
    )
    assert resp.json()["code"] == 0, resp.text
    return resp.json()["data"]["id"]


class TestFeeRule:
    def test_create_and_list(self, client, admin_headers):
        resp = client.post(
            "/api/v1/fee-rules",
            headers=admin_headers,
            json={"name": "规则A", "free_minutes": 30, "first_hour_fee": 8, "hourly_fee": 5, "daily_cap": 60},
        )
        assert resp.json()["code"] == 0
        rows = client.get("/api/v1/fee-rules", headers=admin_headers).json()["data"]
        assert any(r["id"] == resp.json()["data"]["id"] for r in rows)

    def test_officer_cannot_create_rule(self, client, officer_headers):
        resp = client.post(
            "/api/v1/fee-rules",
            headers=officer_headers,
            json={"name": "x", "free_minutes": 0, "first_hour_fee": 1, "hourly_fee": 1, "daily_cap": 1},
        )
        assert resp.status_code == 403


class TestEnterExit:
    def test_enter_creates_inside_record(self, client, admin_headers):
        lot_id = _new_lot(client, admin_headers)
        plate = _plate()
        resp2 = client.post(
            "/api/v1/parking/enter",
            headers=admin_headers,
            data={"parking_lot_id": str(lot_id), "plate_no": plate},
        )
        body = resp2.json()
        assert body["code"] == 0, body
        record_id = body["data"]["record_id"]
        rows = client.get(
            "/api/v1/parking-records", headers=admin_headers, params={"parking_lot_id": lot_id, "status": "inside"}
        ).json()["data"]
        assert any(r["id"] == record_id and r["plate_no"] == plate for r in rows["list"])

    def test_duplicate_enter_rejected(self, client, admin_headers):
        lot_id = _new_lot(client, admin_headers)
        plate = _plate()
        client.post("/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": plate})
        resp = client.post("/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": plate})
        assert resp.json()["code"] == 30002

    def test_full_lot_rejected(self, client, admin_headers):
        lot_id = _new_lot(client, admin_headers, total=1)
        client.post("/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": _plate()})
        resp = client.post("/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": _plate()})
        assert resp.json()["code"] == 30001

    def test_invalid_plate_rejected(self, client, admin_headers):
        lot_id = _new_lot(client, admin_headers)
        resp = client.post("/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": "BAD123"})
        assert resp.json()["code"] == 20002

    def test_exit_settles_fee(self, client, admin_headers, db_session):
        from datetime import datetime, timedelta

        from app.models import ParkingRecord

        lot_id = _new_lot(client, admin_headers, with_rule=True)
        plate = _plate()
        resp = client.post(
            "/api/v1/parking/enter", headers=admin_headers, data={"parking_lot_id": str(lot_id), "plate_no": plate}
        ).json()
        # 把入场时间拨回 3 小时前，构造约 195 分钟（免费 15 → 3 小时 → 5+2*3=11 元）
        record = db_session.get(ParkingRecord, resp["data"]["record_id"])
        record.enter_time = datetime.now() - timedelta(minutes=195)
        db_session.commit()
        resp = client.post(
            "/api/v1/parking/exit", headers=admin_headers, json={"parking_lot_id": lot_id, "plate_no": plate}
        )
        body = resp.json()
        assert body["code"] == 0, body
        # 出场时刻与推算存在分钟级误差，验证费用落在合理区间（3 小时 → 11 元上下）
        assert 8.0 <= body["data"]["fee"] <= 14.0, body["data"]

    def test_exit_without_inside_record(self, client, admin_headers):
        lot_id = _new_lot(client, admin_headers)
        resp = client.post("/api/v1/parking/exit", headers=admin_headers, json={"parking_lot_id": lot_id, "plate_no": _plate()})
        assert resp.json()["code"] == 30003

    def test_user_cannot_enter_but_can_view_lots(self, client, user_headers, admin_headers):
        lot_id = _new_lot(client, admin_headers)
        resp = client.post("/api/v1/parking/enter", headers=user_headers, data={"parking_lot_id": str(lot_id), "plate_no": _plate()})
        assert resp.status_code == 403
        assert client.get("/api/v1/parking-lots", headers=user_headers).status_code == 200
        # 普通用户不可看出入场记录列表
        assert client.get("/api/v1/parking-records", headers=user_headers).status_code == 403
