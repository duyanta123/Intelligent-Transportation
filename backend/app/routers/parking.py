"""智慧停车：停车场 CRUD、计费规则 CRUD、出入场与结算"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import (
    E_NOT_FOUND,
    E_PARKING_DUP,
    E_PARKING_FULL,
    E_PARKING_NO_RECORD,
    BizError,
    ok,
)
from app.models import FeeRule, ParkingLot, ParkingRecord, User
from app.schemas import FeeRuleIn, ParkingEnterIn, ParkingExitIn, ParkingLotIn
from app.services.algorithms import calc_parking_fee_dt
from app.services.oplog import log_op
from app.utils.upload import save_image
from app.utils.validators import (
    clamp_page,
    is_valid_plate,
    normalize_plate,
    to_local_naive,
)

router = APIRouter(tags=["智慧停车"])


def _lot_out(lot: ParkingLot, rule: FeeRule | None = None) -> dict:
    return {
        "id": lot.id,
        "name": lot.name,
        "address": lot.address,
        "total_slots": lot.total_slots,
        "used_slots": lot.used_slots,
        "free_slots": max(0, lot.total_slots - lot.used_slots),
        "occupancy": round(lot.used_slots / max(1, lot.total_slots) * 100, 1),
        "fee_rule_id": lot.fee_rule_id,
        "fee_rule_name": rule.name if rule else "",
    }


@router.get("/parking-lots")
def list_lots(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer", "user"))):
    """停车场列表（普通用户可查看剩余车位）"""
    rules = {r.id: r for r in db.query(FeeRule).filter(FeeRule.is_deleted == 0).all()}
    rows = db.query(ParkingLot).filter(ParkingLot.is_deleted == 0).order_by(ParkingLot.id).all()
    return ok([_lot_out(lot, rules.get(lot.fee_rule_id)) for lot in rows])


@router.post("/parking-lots")
def create_lot(
    body: ParkingLotIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    lot = ParkingLot(**body.model_dump())
    db.add(lot)
    db.flush()
    log_op(db, request, admin_user, "新增", f"新增停车场：{lot.name}")
    db.commit()
    return ok({"id": lot.id}, "创建成功")


@router.put("/parking-lots/{item_id}")
def update_lot(
    item_id: int, body: ParkingLotIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    lot = db.query(ParkingLot).filter(ParkingLot.id == item_id, ParkingLot.is_deleted == 0).first()
    if lot is None:
        raise BizError(*E_NOT_FOUND)
    for field, value in body.model_dump().items():
        setattr(lot, field, value)
    log_op(db, request, admin_user, "修改", f"修改停车场：{lot.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/parking-lots/{item_id}")
def delete_lot(
    item_id: int, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    lot = db.query(ParkingLot).filter(ParkingLot.id == item_id, ParkingLot.is_deleted == 0).first()
    if lot is None:
        raise BizError(*E_NOT_FOUND)
    lot.is_deleted = 1
    log_op(db, request, admin_user, "删除", f"删除停车场：{lot.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


# ---------------- 计费规则 ----------------
@router.get("/fee-rules")
def list_fee_rules(admin_user: User = Depends(require_roles("admin", "officer", "user")), db: Session = Depends(get_db)):
    rows = db.query(FeeRule).filter(FeeRule.is_deleted == 0).order_by(FeeRule.id).all()
    return ok(
        [
            {
                "id": r.id,
                "name": r.name,
                "free_minutes": r.free_minutes,
                "first_hour_fee": float(r.first_hour_fee),
                "hourly_fee": float(r.hourly_fee),
                "daily_cap": float(r.daily_cap),
            }
            for r in rows
        ]
    )


@router.post("/fee-rules")
def create_fee_rule(
    body: FeeRuleIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    rule = FeeRule(**body.model_dump())
    db.add(rule)
    db.flush()
    log_op(db, request, admin_user, "新增", f"新增计费规则：{rule.name}")
    db.commit()
    return ok({"id": rule.id}, "创建成功")


@router.put("/fee-rules/{item_id}")
def update_fee_rule(
    item_id: int, body: FeeRuleIn, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    rule = db.query(FeeRule).filter(FeeRule.id == item_id, FeeRule.is_deleted == 0).first()
    if rule is None:
        raise BizError(*E_NOT_FOUND)
    for field, value in body.model_dump().items():
        setattr(rule, field, value)
    log_op(db, request, admin_user, "修改", f"修改计费规则：{rule.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/fee-rules/{item_id}")
def delete_fee_rule(
    item_id: int, request: Request, admin_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    rule = db.query(FeeRule).filter(FeeRule.id == item_id, FeeRule.is_deleted == 0).first()
    if rule is None:
        raise BizError(*E_NOT_FOUND)
    rule.is_deleted = 1
    log_op(db, request, admin_user, "删除", f"删除计费规则：{rule.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


# ---------------- 出入场 ----------------
@router.post("/parking/enter")
def parking_enter(
    request: Request,
    parking_lot_id: int = Form(...),
    plate_no: str = Form(...),
    file: UploadFile | None = File(None),
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """入场登记（multipart 表单）：可携带入场拍照；车牌重复入场校验、满位校验。

    同步端点（FastAPI 自动丢线程池），避免 save_image 与 DB 阻塞事件循环。
    """
    body = ParkingEnterIn(parking_lot_id=parking_lot_id, plate_no=plate_no)
    plate = normalize_plate(body.plate_no)
    if not is_valid_plate(plate):
        raise BizError(20002, "车牌号格式不正确", 400)
    # 行锁（FOR UPDATE）串行化同一停车场的并发入场：防止满位超卖、
    # 同车牌重复入场、used_slots 读改写丢失更新
    lot = (
        db.query(ParkingLot)
        .filter(ParkingLot.id == body.parking_lot_id, ParkingLot.is_deleted == 0)
        .with_for_update()
        .first()
    )
    if lot is None:
        raise BizError(*E_NOT_FOUND)
    dup = (
        db.query(ParkingRecord)
        .filter(
            ParkingRecord.parking_lot_id == lot.id,
            ParkingRecord.plate_no == plate,
            ParkingRecord.status == "inside",
            ParkingRecord.is_deleted == 0,
        )
        .first()
    )
    if dup:
        raise BizError(*E_PARKING_DUP)
    if lot.used_slots >= lot.total_slots:
        raise BizError(*E_PARKING_FULL)
    image_url = save_image(file)
    record = ParkingRecord(
        parking_lot_id=lot.id,
        plate_no=plate,
        enter_time=datetime.now(),
        status="inside",
        image_url=image_url,
    )
    lot.used_slots += 1
    db.add(record)
    db.flush()
    log_op(db, request, current_user, "入场", f"车辆 {plate} 进入 {lot.name}")
    db.commit()
    return ok({"record_id": record.id, "plate_no": plate, "enter_time": record.enter_time.strftime("%Y-%m-%d %H:%M:%S")}, "入场成功")


@router.post("/parking/exit")
def parking_exit(
    body: ParkingExitIn,
    request: Request,
    current_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    """出场结算：按计费规则计算费用（免费时长/首小时/每小时/单日封顶）。

    与入场共用停车场行锁：并发双击出场时第二个事务会在记录状态检查处被拒。
    """
    plate = normalize_plate(body.plate_no)
    lot = (
        db.query(ParkingLot)
        .filter(ParkingLot.id == body.parking_lot_id, ParkingLot.is_deleted == 0)
        .with_for_update()
        .first()
    )
    if lot is None:
        raise BizError(*E_NOT_FOUND)
    record = (
        db.query(ParkingRecord)
        .filter(
            ParkingRecord.parking_lot_id == lot.id,
            ParkingRecord.plate_no == plate,
            ParkingRecord.status == "inside",
            ParkingRecord.is_deleted == 0,
        )
        .order_by(ParkingRecord.enter_time.desc())
        .first()
    )
    if record is None:
        raise BizError(*E_PARKING_NO_RECORD)
    rule = db.query(FeeRule).filter(FeeRule.id == lot.fee_rule_id, FeeRule.is_deleted == 0).first() if lot.fee_rule_id else None
    exit_time = datetime.now()
    fee = 0.0
    if rule:
        fee = calc_parking_fee_dt(
            record.enter_time, exit_time, rule.free_minutes, float(rule.first_hour_fee), float(rule.hourly_fee), float(rule.daily_cap)
        )
    record.exit_time = exit_time
    record.fee = fee
    record.status = "finished"
    lot.used_slots = max(0, lot.used_slots - 1)
    log_op(db, request, current_user, "出场", f"车辆 {plate} 驶出 {lot.name}，结算 {fee} 元")
    db.commit()
    return ok(
        {
            "record_id": record.id,
            "plate_no": plate,
            "enter_time": record.enter_time.strftime("%Y-%m-%d %H:%M:%S"),
            "exit_time": exit_time.strftime("%Y-%m-%d %H:%M:%S"),
            "fee": fee,
        },
        "出场结算成功",
    )


@router.get("/parking-records")
def list_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    plate_no: str = Query(""),
    parking_lot_id: int | None = Query(None),
    status: str = Query(""),
    enter_start: datetime | None = Query(None, description="入场时间起"),
    enter_end: datetime | None = Query(None, description="入场时间止"),
    admin_user: User = Depends(require_roles("admin", "officer")),
    db: Session = Depends(get_db),
):
    page, size = clamp_page(page, size)
    query = db.query(ParkingRecord).filter(ParkingRecord.is_deleted == 0)
    if plate_no:
        query = query.filter(ParkingRecord.plate_no.like(f"%{normalize_plate(plate_no)}%"))
    if parking_lot_id:
        query = query.filter(ParkingRecord.parking_lot_id == parking_lot_id)
    if status:
        query = query.filter(ParkingRecord.status == status)
    if enter_start:
        query = query.filter(ParkingRecord.enter_time >= to_local_naive(enter_start))
    if enter_end:
        # DATETIME 秒级四舍五入竞态：上界预留 1 秒缓冲
        query = query.filter(ParkingRecord.enter_time <= to_local_naive(enter_end) + timedelta(seconds=1))
    total = query.count()
    rows = query.order_by(ParkingRecord.id.desc()).offset((page - 1) * size).limit(size).all()
    lots = {lot.id: lot.name for lot in db.query(ParkingLot).filter(ParkingLot.is_deleted == 0).all()}
    return ok(
        {
            "list": [
                {
                    "id": r.id,
                    "parking_lot_id": r.parking_lot_id,
                    "parking_lot_name": lots.get(r.parking_lot_id, ""),
                    "plate_no": r.plate_no,
                    "enter_time": r.enter_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "exit_time": r.exit_time.strftime("%Y-%m-%d %H:%M:%S") if r.exit_time else None,
                    "fee": float(r.fee) if r.fee is not None else None,
                    "status": r.status,
                    "image_url": r.image_url,
                }
                for r in rows
            ],
            "total": total,
            "page": page,
            "size": size,
        }
    )
