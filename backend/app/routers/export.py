# -*- coding: utf-8 -*-
"""报表导出路由：违章明细 / 出入场记录 / 流量日报（admin/officer，xlsx 下载）"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.models import ParkingLot, ParkingRecord, RoadSection, TrafficFlow, User, Violation
from app.services.excel_service import build_xlsx

router = APIRouter(prefix="/export", tags=["报表导出"])

LEVEL_NAMES = ["自由流", "缓行", "拥堵", "严重拥堵"]
VIOLATION_STATUS_NAMES = {"pending": "待审核", "confirmed": "已确认", "rejected": "已驳回", "processed": "已处理"}


def _xlsx_response(filename: str, title: str, headers: list[str], rows: list[list]) -> StreamingResponse:
    content = build_xlsx(title, headers, rows)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/violations.xlsx")
def export_violations(
    days: int = Query(30, ge=1, le=365, description="导出最近 N 天"),
    _: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    start = datetime.now() - timedelta(days=days)
    rows_db = (
        db.query(Violation)
        .filter(Violation.is_deleted == 0, Violation.violation_time >= start)
        .order_by(Violation.violation_time.desc())
        .limit(5000)
        .all()
    )
    from app.models import Intersection

    inter_names = {i.id: i.name for i in db.query(Intersection).filter(Intersection.is_deleted == 0).all()}
    rows = [
        [
            v.id,
            v.plate_no,
            v.violation_type,
            v.violation_time.strftime("%Y-%m-%d %H:%M:%S"),
            inter_names.get(v.intersection_id, ""),
            float(v.fine_amount),
            v.deduct_points,
            VIOLATION_STATUS_NAMES.get(v.status, v.status),
            v.audit_remark,
        ]
        for v in rows_db
    ]
    headers = ["ID", "车牌号", "违章类型", "违章时间", "地点", "罚款(元)", "记分", "状态", "审核备注"]
    return _xlsx_response(f"violations_{datetime.now():%Y%m%d}.xlsx", f"违章明细（近 {days} 天）", headers, rows)


@router.get("/parking-records.xlsx")
def export_parking_records(
    days: int = Query(30, ge=1, le=365),
    _: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    start = datetime.now() - timedelta(days=days)
    rows_db = (
        db.query(ParkingRecord)
        .filter(ParkingRecord.is_deleted == 0, ParkingRecord.enter_time >= start)
        .order_by(ParkingRecord.enter_time.desc())
        .limit(5000)
        .all()
    )
    lot_names = {lot.id: lot.name for lot in db.query(ParkingLot).filter(ParkingLot.is_deleted == 0).all()}
    rows = [
        [
            r.id,
            lot_names.get(r.parking_lot_id, ""),
            r.plate_no,
            r.enter_time.strftime("%Y-%m-%d %H:%M:%S"),
            r.exit_time.strftime("%Y-%m-%d %H:%M:%S") if r.exit_time else "在场",
            float(r.fee) if r.fee is not None else "",
            "已出场" if r.status == "finished" else "在场",
        ]
        for r in rows_db
    ]
    headers = ["ID", "停车场", "车牌号", "入场时间", "出场时间", "费用(元)", "状态"]
    return _xlsx_response(f"parking_{datetime.now():%Y%m%d}.xlsx", f"出入场记录（近 {days} 天）", headers, rows)


@router.get("/traffic-report.xlsx")
def export_traffic_report(
    days: int = Query(7, ge=1, le=60, description="日报天数"),
    _: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """流量日报：每路段每天的平均流率/峰值/平均车速/拥堵时长占比"""
    start = datetime.now() - timedelta(days=days)
    fmt = "%Y-%m-%d"
    rows_db = (
        db.query(
            RoadSection.name.label("section"),
            func.date_format(TrafficFlow.recorded_at, fmt).label("day"),
            func.round(func.avg(TrafficFlow.flow), 0).label("avg_flow"),
            func.max(TrafficFlow.flow).label("max_flow"),
            func.round(func.avg(TrafficFlow.speed), 1).label("avg_speed"),
            func.sum(func.if_(TrafficFlow.congestion_level >= 2, 1, 0)).label("congested"),
            func.count(TrafficFlow.id).label("total"),
        )
        .join(RoadSection, RoadSection.id == TrafficFlow.road_section_id)
        .filter(TrafficFlow.is_deleted == 0, TrafficFlow.recorded_at >= start)
        .group_by(RoadSection.name, "day")
        .order_by(func.min(TrafficFlow.recorded_at), RoadSection.name)
        .limit(2000)
        .all()
    )
    rows = [
        [
            r.day,
            r.section,
            float(r.avg_flow or 0),
            float(r.max_flow or 0),
            float(r.avg_speed or 0),
            f"{(float(r.congested or 0) / max(1, r.total) * 100):.1f}%",
        ]
        for r in rows_db
    ]
    headers = ["日期", "路段", "平均流率(pcu/h)", "峰值流率(pcu/h)", "平均车速(km/h)", "拥堵占比"]
    return _xlsx_response(f"traffic_{datetime.now():%Y%m%d}.xlsx", f"路段流量日报（近 {days} 天）", headers, rows)
