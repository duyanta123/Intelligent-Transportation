"""车辆与违章管理：车辆 CRUD、违章录入/列表/审核/类型字典"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import (
    E_NOT_FOUND,
    E_PLATE_DUPLICATE,
    E_PLATE_INVALID,
    E_VIOLATION_AUDITED,
    E_VIOLATION_PROCESS_DENIED,
    BizError,
    ok,
)
from app.models import User, Vehicle, Violation
from app.schemas import VehicleIn, ViolationAuditIn, ViolationIn
from app.services.oplog import log_op
from app.utils.validators import clamp_page, normalize_plate, to_local_naive

router = APIRouter(tags=["车辆与违章"])

# 违章类型字典：类型 -> (罚款, 扣分)
VIOLATION_TYPES = [
    {"code": "闯红灯", "fine": 200, "points": 6},
    {"code": "超速", "fine": 200, "points": 3},
    {"code": "违停", "fine": 150, "points": 0},
    {"code": "不按导向车道行驶", "fine": 100, "points": 2},
]
VIOLATION_STATUS = {"pending": "待审核", "confirmed": "已确认", "rejected": "已驳回", "processed": "已处理"}


@router.get("/violation-types")
def violation_types(current_user: User = Depends(require_roles("admin", "officer", "user"))):
    return ok(
        [{"code": t["code"], "fine": t["fine"], "points": t["points"]} for t in VIOLATION_TYPES]
        + [{"status": k, "name": v} for k, v in VIOLATION_STATUS.items()]
    )


# ---------------- 车辆 ----------------
@router.get("/vehicles")
def list_vehicles(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    keyword: str = Query("", description="车牌号/车主/手机号"),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
    db: Session = Depends(get_db),
):
    page, size = clamp_page(page, size)
    query = db.query(Vehicle).filter(Vehicle.is_deleted == 0)
    # 普通用户仅能查看本人登记车辆
    if _role_of(db, current_user) == "user":
        query = query.filter(Vehicle.user_id == current_user.id)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            or_(Vehicle.plate_no.like(like), Vehicle.owner_name.like(like), Vehicle.owner_phone.like(like))
        )
    total = query.count()
    rows = query.order_by(Vehicle.id.desc()).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_vehicle_out(v) for v in rows], "total": total, "page": page, "size": size})


def _role_of(db: Session, user: User) -> str:
    from app.services.auth_service import get_user_role_code

    return get_user_role_code(db, user)


def _vehicle_out(v: Vehicle) -> dict:
    return {
        "id": v.id,
        "user_id": v.user_id,
        "plate_no": v.plate_no,
        "vehicle_type": v.vehicle_type,
        "color": v.color,
        "owner_name": v.owner_name,
        "owner_phone": v.owner_phone,
        "created_at": v.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.post("/vehicles")
def create_vehicle(
    body: VehicleIn, request: Request, current_user: User = Depends(require_roles("admin", "officer")), db: Session = Depends(get_db)
):
    plate = normalize_plate(body.plate_no)
    if not _is_plate_valid(plate):
        raise BizError(*E_PLATE_INVALID)
    exists = db.query(Vehicle).filter(Vehicle.plate_no == plate, Vehicle.is_deleted == 0).first()
    if exists:
        raise BizError(*E_PLATE_DUPLICATE)
    vehicle = Vehicle(**body.model_dump())
    vehicle.plate_no = plate
    db.add(vehicle)
    try:
        db.flush()
    except IntegrityError as err:
        # 并发登记同一车牌时唯一索引兜底（查询查重与插入之间存在竞态窗口）
        db.rollback()
        raise BizError(*E_PLATE_DUPLICATE) from err
    log_op(db, request, current_user, "新增", f"登记车辆：{plate}")
    db.commit()
    return ok({"id": vehicle.id}, "登记成功")


def _is_plate_valid(plate: str) -> bool:
    from app.utils.validators import is_valid_plate

    return is_valid_plate(plate)


@router.put("/vehicles/{item_id}")
def update_vehicle(
    item_id: int,
    body: VehicleIn,
    request: Request,
    admin_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == item_id, Vehicle.is_deleted == 0).first()
    if vehicle is None:
        raise BizError(*E_NOT_FOUND)
    plate = normalize_plate(body.plate_no)
    if not _is_plate_valid(plate):
        raise BizError(*E_PLATE_INVALID)
    # 改车牌查重（排除自身），否则撞唯一索引直接 500
    dup = db.query(Vehicle).filter(Vehicle.plate_no == plate, Vehicle.is_deleted == 0, Vehicle.id != item_id).first()
    if dup:
        raise BizError(*E_PLATE_DUPLICATE)
    data = body.model_dump()
    data["plate_no"] = plate
    for field, value in data.items():
        setattr(vehicle, field, value)
    try:
        db.flush()
    except IntegrityError as err:
        db.rollback()
        raise BizError(*E_PLATE_DUPLICATE) from err
    log_op(db, request, admin_user, "修改", f"修改车辆信息：{plate}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/vehicles/{item_id}")
def delete_vehicle(
    item_id: int, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == item_id, Vehicle.is_deleted == 0).first()
    if vehicle is None:
        raise BizError(*E_NOT_FOUND)
    # 软删除 + 车牌改写墓碑：plate_no 有唯一索引，若保留原值，
    # 该车牌将永远无法重新登记（INSERT 撞唯一键报 500）。
    # 墓碑后缀 *{id} 保证全局唯一；历史违章记录存的是原字符串，不受影响。
    original_plate = vehicle.plate_no
    vehicle.is_deleted = 1
    vehicle.plate_no = f"{original_plate}*{vehicle.id}"[:16]
    log_op(db, request, admin_user, "删除", f"删除车辆：{original_plate}（软删除）")
    db.commit()
    return ok(None, "删除成功")


# ---------------- 违章 ----------------
@router.get("/violations/stats")
def violation_stats(
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """按状态统计违章数量（供管理页 Tab 徽标）"""
    rows = (
        db.query(Violation.status, func.count(Violation.id))
        .filter(Violation.is_deleted == 0)
        .group_by(Violation.status)
        .all()
    )
    counts = {status: int(c) for status, c in rows}
    return ok({**counts, "total": sum(counts.values())})



@router.get("/violations")
def list_violations(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    plate_no: str = Query(""),
    violation_type: str = Query(""),
    status: str = Query(""),
    current_user: User = Depends(require_roles("admin", "officer", "user")),
    db: Session = Depends(get_db),
):
    page, size = clamp_page(page, size)
    query = db.query(Violation).filter(Violation.is_deleted == 0)
    if _role_of(db, current_user) == "user":
        # 普通用户仅可查询本人车辆的违章
        own_plates = [
            v.plate_no
            for v in db.query(Vehicle).filter(Vehicle.user_id == current_user.id, Vehicle.is_deleted == 0).all()
        ]
        query = query.filter(Violation.plate_no.in_(own_plates or ["__none__"]))
    if plate_no:
        query = query.filter(Violation.plate_no.like(f"%{normalize_plate(plate_no)}%"))
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
    if status:
        query = query.filter(Violation.status == status)
    total = query.count()
    rows = query.order_by(Violation.violation_time.desc()).offset((page - 1) * size).limit(size).all()
    return ok({"list": [_violation_out(v) for v in rows], "total": total, "page": page, "size": size})


def _violation_out(v: Violation) -> dict:
    return {
        "id": v.id,
        "vehicle_id": v.vehicle_id,
        "plate_no": v.plate_no,
        "intersection_id": v.intersection_id,
        "violation_type": v.violation_type,
        "violation_time": v.violation_time.strftime("%Y-%m-%d %H:%M:%S"),
        "fine_amount": float(v.fine_amount),
        "deduct_points": v.deduct_points,
        "status": v.status,
        "status_name": VIOLATION_STATUS.get(v.status, v.status),
        "evidence_url": v.evidence_url,
        "audit_by": v.audit_by,
        "audit_remark": v.audit_remark,
        "audit_time": v.audit_time.strftime("%Y-%m-%d %H:%M:%S") if v.audit_time else None,
        "remark": v.remark,
    }


@router.post("/violations")
def create_violation(
    body: ViolationIn, request: Request, current_user: User = Depends(require_roles("admin", "officer")), db: Session = Depends(get_db)
):
    plate = normalize_plate(body.plate_no)
    if not _is_plate_valid(plate):
        raise BizError(*E_PLATE_INVALID)
    vehicle = db.query(Vehicle).filter(Vehicle.plate_no == plate, Vehicle.is_deleted == 0).first()
    if vehicle is not None:
        vehicle_id = vehicle.id
    elif body.vehicle_id is not None:
        # 车牌未登记时才允许使用显式 vehicle_id，且必须真实存在（防止挂到任意/不存在车辆）
        ref = db.query(Vehicle).filter(Vehicle.id == body.vehicle_id, Vehicle.is_deleted == 0).first()
        if ref is None:
            raise BizError(*E_NOT_FOUND)
        vehicle_id = ref.id
    else:
        vehicle_id = None
    item = Violation(
        vehicle_id=vehicle_id,
        plate_no=plate,
        intersection_id=body.intersection_id,
        violation_type=body.violation_type,
        violation_time=to_local_naive(body.violation_time) or datetime.now(),
        fine_amount=body.fine_amount,
        deduct_points=body.deduct_points,
        evidence_url=body.evidence_url,
        remark=body.remark,
        status="pending",
    )
    db.add(item)
    db.flush()
    log_op(db, request, current_user, "录入", f"录入违章：{plate} {body.violation_type}")
    db.commit()
    return ok({"id": item.id}, "录入成功，等待审核")


@router.post("/violations/{item_id}/audit")
def audit_violation(
    item_id: int,
    body: ViolationAuditIn,
    request: Request,
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """审核违章：通过（confirmed）或驳回（rejected），可再次标记已处理"""
    item = db.query(Violation).filter(Violation.id == item_id, Violation.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    if item.status in ("confirmed", "rejected", "processed"):
        raise BizError(*E_VIOLATION_AUDITED)
    item.status = body.result
    item.audit_by = current_user.id
    item.audit_remark = body.remark
    item.audit_time = datetime.now()
    action = "审核通过" if body.result == "confirmed" else "审核驳回"
    log_op(db, request, current_user, "审核", f"{action}违章记录 #{item.id}（{item.plate_no}）")
    db.commit()
    return ok(_violation_out(item), f"已{action}")


@router.post("/violations/{item_id}/process")
def process_violation(
    item_id: int, request: Request, current_user: User = Depends(require_roles("admin", "officer")), db: Session = Depends(get_db)
):
    """状态流转：已确认 -> 已处理（罚款缴纳/扣分执行）"""
    item = db.query(Violation).filter(Violation.id == item_id, Violation.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    if item.status != "confirmed":
        raise BizError(*E_VIOLATION_PROCESS_DENIED)
    item.status = "processed"
    log_op(db, request, current_user, "处理", f"违章记录 #{item.id}（{item.plate_no}）处理完毕")
    db.commit()
    return ok(_violation_out(item), "已标记为已处理")
