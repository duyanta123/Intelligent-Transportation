"""路况监测：路段 CRUD、流量上报、历史查询、实时拥堵"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import E_NOT_FOUND, BizError, ok
from app.models import Intersection, RoadSection, TrafficFlow, User
from app.schemas import FlowReportIn, RoadSectionIn
from app.services.algorithms import (
    CAPACITY_PER_LANE,
    congestion_level,
    speed_by_saturation,
)
from app.services.oplog import log_op
from app.utils.validators import clamp_page

router = APIRouter(tags=["路况监测"])


@router.get("/road-sections")
def list_sections(
    keyword: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
):
    """路段列表（所有登录角色可见，供路况查询）"""
    query = db.query(RoadSection).filter(RoadSection.is_deleted == 0)
    if keyword:
        query = query.filter(RoadSection.name.like(f"%{keyword}%"))
    rows = query.order_by(RoadSection.id).all()
    names = {i.id: i.name for i in db.query(Intersection).filter(Intersection.is_deleted == 0).all()}
    return ok(
        [
            {
                "id": s.id,
                "name": s.name,
                "start_intersection_id": s.start_intersection_id,
                "end_intersection_id": s.end_intersection_id,
                "start_name": names.get(s.start_intersection_id, ""),
                "end_name": names.get(s.end_intersection_id, ""),
                "lane_count": s.lane_count,
                "length_km": float(s.length_km),
                "direction": s.direction,
                "capacity": s.capacity,
            }
            for s in rows
        ]
    )


@router.post("/road-sections")
def create_section(
    body: RoadSectionIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = RoadSection(**body.model_dump())
    item.capacity = int(item.lane_count * CAPACITY_PER_LANE)
    db.add(item)
    db.flush()
    log_op(db, request, admin_user, "新增", f"新增路段：{item.name}")
    db.commit()
    return ok({"id": item.id}, "创建成功")


@router.put("/road-sections/{item_id}")
def update_section(
    item_id: int, body: RoadSectionIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = db.query(RoadSection).filter(RoadSection.id == item_id, RoadSection.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    data = body.model_dump()
    for field, value in data.items():
        setattr(item, field, value)
    item.capacity = int(item.lane_count * CAPACITY_PER_LANE)
    log_op(db, request, admin_user, "修改", f"修改路段：{item.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/road-sections/{item_id}")
def delete_section(
    item_id: int, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = db.query(RoadSection).filter(RoadSection.id == item_id, RoadSection.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    item.is_deleted = 1
    log_op(db, request, admin_user, "删除", f"删除路段：{item.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


def _insert_flow(db: Session, section: RoadSection, flow_rate: int, speed: float | None, recorded_at: datetime | None = None):
    """按流率写一条流量记录：饱和度=流率/通行能力，自动分级与推算车速"""
    saturation = round(min(1.2, flow_rate / max(1, section.capacity)), 3)
    if speed is None:
        speed = speed_by_saturation(55.0, saturation)
    row = TrafficFlow(
        road_section_id=section.id,
        recorded_at=recorded_at or datetime.now(),
        flow=int(flow_rate),
        speed=speed,
        saturation=saturation,
        congestion_level=congestion_level(saturation),
    )
    db.add(row)
    return row


@router.post("/traffic-flow/report")
def report_flow(
    body: FlowReportIn, request: Request, current_user: User = Depends(require_roles("admin", "officer")), db: Session = Depends(get_db)
):
    """模拟上报接口：上报该分钟检测到的车辆数，内部折算为小时流率（×60）"""
    section = db.query(RoadSection).filter(RoadSection.id == body.road_section_id, RoadSection.is_deleted == 0).first()
    if section is None:
        raise BizError(*E_NOT_FOUND)
    row = _insert_flow(db, section, body.flow * 60, body.speed)
    log_op(db, request, current_user, "上报", f"路段[{section.name}]流量上报 {body.flow} 辆/分钟")
    db.commit()
    return ok(
        {
            "id": row.id,
            "flow": row.flow,
            "speed": float(row.speed),
            "saturation": float(row.saturation),
            "congestion_level": row.congestion_level,
        },
        "上报成功",
    )


@router.get("/traffic-flow/history")
def flow_history(
    road_section_id: int | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    granularity: str = Query("hour", pattern=r"^(hour|day)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500, description="聚合数据轻量，放宽至 500 支撑对比模式"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
):
    """历史流量查询：按小时/天聚合（平均流率与平均车速、峰值）"""
    page, size = clamp_page(page, size)
    end = end or datetime.now()
    start = start or end - timedelta(days=7)
    # MySQL DATETIME 写入时对小数秒四舍五入（0.6s 会进位到下一秒），
    # 此处 end 预留 1 秒缓冲，避免刚写入的记录被排除（秒边界竞态）
    end = end + timedelta(seconds=1)
    fmt = "%Y-%m-%d %H:00:00" if granularity == "hour" else "%Y-%m-%d 00:00:00"

    base = db.query(
        func.date_format(TrafficFlow.recorded_at, fmt).label("bucket"),
        func.round(func.avg(TrafficFlow.flow), 0).label("avg_flow"),
        func.max(TrafficFlow.flow).label("max_flow"),
        func.round(func.avg(TrafficFlow.speed), 1).label("avg_speed"),
        func.count(TrafficFlow.id).label("samples"),
    ).filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= start, TrafficFlow.recorded_at <= end)
    if road_section_id:
        base = base.filter(TrafficFlow.road_section_id == road_section_id)
    rows = (
        base.group_by("bucket")
        .order_by(func.min(TrafficFlow.recorded_at))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    count_query = (
        db.query(func.count(func.distinct(func.date_format(TrafficFlow.recorded_at, fmt))))
        .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= start, TrafficFlow.recorded_at <= end)
    )
    if road_section_id:
        count_query = count_query.filter(TrafficFlow.road_section_id == road_section_id)
    total = count_query.scalar() or 0
    return ok(
        {
            "list": [
                {
                    "time": r.bucket,
                    "avg_flow": float(r.avg_flow or 0),
                    "max_flow": float(r.max_flow or 0),
                    "avg_speed": float(r.avg_speed or 0),
                    "samples": r.samples,
                }
                for r in rows
            ],
            "total": int(total),
            "page": page,
            "size": size,
        }
    )


LEVEL_NAMES = ["自由流", "缓行", "拥堵", "严重拥堵"]


@router.get("/traffic-flow/congestion")
def congestion_now(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
):
    """实时拥堵：取每条路段最近一条流量记录，并映射到路口（供大屏地图散点）"""
    latest_sq = (
        db.query(TrafficFlow.road_section_id, func.max(TrafficFlow.id).label("max_id"))
        .filter(TrafficFlow.is_deleted == 0)
        .group_by(TrafficFlow.road_section_id)
        .subquery()
    )
    rows = (
        db.query(TrafficFlow, RoadSection)
        .join(latest_sq, latest_sq.c.max_id == TrafficFlow.id)
        .join(RoadSection, RoadSection.id == TrafficFlow.road_section_id)
        .filter(TrafficFlow.is_deleted == 0)
        .all()
    )
    intersections = db.query(Intersection).filter(Intersection.is_deleted == 0).all()
    # 路口实时状态：取与该路口相连路段的最高拥堵等级
    section_level: dict[int, dict] = {}
    for flow, section in rows:
        level = flow.congestion_level
        for iid in (section.start_intersection_id, section.end_intersection_id):
            cur = section_level.get(iid)
            if cur is None or level > cur["level"]:
                section_level[iid] = {"level": level, "flow": flow.flow, "speed": float(flow.speed)}
    return ok(
        {
            "sections": [
                {
                    "road_section_id": section.id,
                    "name": section.name,
                    "flow": flow.flow,
                    "speed": float(flow.speed),
                    "saturation": float(flow.saturation),
                    "level": flow.congestion_level,
                    "level_name": LEVEL_NAMES[flow.congestion_level],
                    "recorded_at": flow.recorded_at.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for flow, section in rows
            ],
            "intersections": [
                {
                    "id": i.id,
                    "name": i.name,
                    "longitude": float(i.longitude),
                    "latitude": float(i.latitude),
                    "level": section_level.get(i.id, {}).get("level", 0),
                    "level_name": LEVEL_NAMES[section_level.get(i.id, {}).get("level", 0)],
                    "flow": section_level.get(i.id, {}).get("flow", 0),
                    "speed": section_level.get(i.id, {}).get("speed", 0),
                }
                for i in intersections
            ],
        }
    )
