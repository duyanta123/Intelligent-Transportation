"""数据大屏与管理仪表盘聚合接口

/dashboard/realtime：前端 10 秒轮询，后端 Redis 缓存 TTL 8 秒
/dashboard/summary：系统仪表盘（管理端首页）统计
"""
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_db, require_roles
from app.core.redis_client import KEY_DASHBOARD, get_redis
from app.core.response import ok
from app.models import (
    Feedback,
    Intersection,
    ParkingLot,
    RoadSection,
    SignalStatus,
    TrafficFlow,
    User,
    Vehicle,
    Violation,
)
from app.services.auth_service import get_user_role_code

router = APIRouter(tags=["数据大屏"])

LEVEL_NAMES = ["自由流", "缓行", "拥堵", "严重拥堵"]


def _today_flow_kpi(db: Session) -> float:
    """今日累计车流量：按小时桶求平均流率再求和（小时行与分钟行不重复计数）"""
    start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        db.query(
            func.date_format(TrafficFlow.recorded_at, "%Y-%m-%d %H:00:00").label("bucket"),
            func.avg(TrafficFlow.flow).label("rate"),
        )
        .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= start)
        .group_by("bucket")
        .all()
    )
    return round(sum(float(r.rate or 0) for r in rows), 0)


def _build_realtime(db: Session) -> dict:
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. 最近 24 小时全市流量趋势（按小时桶平均流率）
    trend_rows = (
        db.query(
            func.date_format(TrafficFlow.recorded_at, "%Y-%m-%d %H:00:00").label("bucket"),
            func.round(func.avg(TrafficFlow.flow), 0).label("rate"),
        )
        .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= now - timedelta(hours=24))
        .group_by("bucket")
        .order_by(func.min(TrafficFlow.recorded_at))
        .all()
    )
    flow_trend = [{"time": r.bucket[11:16], "flow": float(r.rate or 0)} for r in trend_rows]

    # 2. 各路口实时拥堵等级（地图散点）
    latest_sq = (
        db.query(TrafficFlow.road_section_id, func.max(TrafficFlow.id).label("max_id"))
        .filter(TrafficFlow.is_deleted == 0)
        .group_by(TrafficFlow.road_section_id)
        .subquery()
    )
    section_rows = (
        db.query(RoadSection, TrafficFlow)
        .join(latest_sq, latest_sq.c.max_id == TrafficFlow.id)
        .join(RoadSection, RoadSection.id == TrafficFlow.road_section_id)
        .all()
    )
    inter_state: dict[int, dict] = {}
    for section, flow in section_rows:
        for iid in (section.start_intersection_id, section.end_intersection_id):
            cur = inter_state.get(iid)
            if cur is None or flow.congestion_level > cur["level"]:
                inter_state[iid] = {"level": flow.congestion_level, "flow": flow.flow, "speed": float(flow.speed)}
    intersections = db.query(Intersection).filter(Intersection.is_deleted == 0).all()
    map_points = [
        {
            "id": i.id,
            "name": i.name,
            "lng": float(i.longitude),
            "lat": float(i.latitude),
            "level": inter_state.get(i.id, {}).get("level", 0),
            "level_name": LEVEL_NAMES[inter_state.get(i.id, {}).get("level", 0)],
            "flow": inter_state.get(i.id, {}).get("flow", 0),
            "speed": inter_state.get(i.id, {}).get("speed", 0),
        }
        for i in intersections
    ]

    # 3. 信号灯状态分布（按当前相位）
    status_rows = db.query(SignalStatus.current_phase, func.count(SignalStatus.id)).group_by(SignalStatus.current_phase).all()
    signal_dist = [{"name": name or "未知", "value": int(cnt)} for name, cnt in status_rows]

    # 4. 今日违章类型 TOP5
    violation_top = [
        {"name": t or "其他", "value": int(c)}
        for t, c in db.query(Violation.violation_type, func.count(Violation.id))
        .filter(Violation.is_deleted == 0, Violation.violation_time >= day_start)
        .group_by(Violation.violation_type)
        .order_by(func.count(Violation.id).desc())
        .limit(5)
        .all()
    ]

    # 5. 停车场车位占用率
    lots = db.query(ParkingLot).filter(ParkingLot.is_deleted == 0).all()
    parking = [
        {
            "name": lot.name,
            "total": lot.total_slots,
            "used": lot.used_slots,
            "rate": round(lot.used_slots / max(1, lot.total_slots) * 100, 1),
        }
        for lot in lots
    ]

    # 6. 今日核心指标卡
    kpi = {
        "today_flow": _today_flow_kpi(db),
        "avg_speed": round(
            float(
                db.query(func.avg(TrafficFlow.speed))
                .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= now - timedelta(hours=1))
                .scalar()
                or 0
            ),
            1,
        ),
        "violation_today": int(
            db.query(func.count(Violation.id)).filter(Violation.is_deleted == 0, Violation.violation_time >= day_start).scalar() or 0
        ),
        "feedback_pending": int(
            db.query(func.count(Feedback.id)).filter(Feedback.is_deleted == 0, Feedback.status.in_(["pending", "processing"])).scalar() or 0
        ),
    }

    return {
        "flow_trend": flow_trend,
        "map_points": map_points,
        "signal_dist": signal_dist,
        "violation_top": violation_top,
        "parking": parking,
        "kpi": kpi,
        "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/dashboard/realtime")
def dashboard_realtime(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
):
    """大屏实时聚合：Redis 缓存 TTL 8 秒，前端 10 秒轮询"""
    redis = get_redis()
    cached = redis.get(KEY_DASHBOARD)
    if cached:
        return ok(json.loads(cached))
    data = _build_realtime(db)
    redis.setex(KEY_DASHBOARD, settings.DASHBOARD_CACHE_TTL_SECONDS, json.dumps(data, ensure_ascii=False))
    return ok(data)


@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer")),
):
    """管理仪表盘：近 7 天流量趋势 + 违章类型分布 + 停车概览（officer 简版不含用户统计）"""
    now = datetime.now()
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    trend = (
        db.query(
            func.date_format(TrafficFlow.recorded_at, "%Y-%m-%d").label("day"),
            func.round(func.avg(TrafficFlow.flow), 0).label("rate"),
        )
        .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= week_start)
        .group_by("day")
        .order_by(func.min(TrafficFlow.recorded_at))
        .all()
    )
    types = (
        db.query(Violation.violation_type, func.count(Violation.id))
        .filter(Violation.is_deleted == 0)
        .group_by(Violation.violation_type)
        .order_by(func.count(Violation.id).desc())
        .all()
    )
    lots = db.query(ParkingLot).filter(ParkingLot.is_deleted == 0).all()
    data = {
        "flow_trend": [{"date": r.day, "flow": float(r.rate or 0)} for r in trend],
        "violation_types": [{"name": t or "其他", "value": int(c)} for t, c in types],
        "parking": [
            {
                "name": lot.name,
                "total": lot.total_slots,
                "used": lot.used_slots,
                "rate": round(lot.used_slots / max(1, lot.total_slots) * 100, 1),
            }
            for lot in lots
        ],
    }
    if get_user_role_code(db, current_user) == "admin":
        data["user_count"] = int(db.query(func.count(User.id)).filter(User.is_deleted == 0).scalar() or 0)
        data["vehicle_count"] = int(db.query(func.count(Vehicle.id)).filter(Vehicle.is_deleted == 0).scalar() or 0)
    return ok(data)
