"""路口与信号灯管理：路口 CRUD、配时方案 CRUD、Webster 计算、实时状态"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import E_NOT_FOUND, BizError, ok
from app.models import Intersection, SignalPlan, SignalStatus, User
from app.schemas import IntersectionIn, SignalPlanIn, WebsterCalcIn
from app.services.algorithms import webster_calc
from app.services.oplog import log_op

router = APIRouter(tags=["路口与信号灯"])


@router.get("/intersections")
def list_intersections(
    keyword: str = Query(""),
    district: str = Query(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer")),
):
    query = db.query(Intersection).filter(Intersection.is_deleted == 0)
    if keyword:
        query = query.filter(Intersection.name.like(f"%{keyword}%"))
    if district:
        query = query.filter(Intersection.district == district)
    rows = query.order_by(Intersection.id).all()
    return ok(
        [
            {
                "id": i.id,
                "name": i.name,
                "longitude": float(i.longitude),
                "latitude": float(i.latitude),
                "lane_count": i.lane_count,
                "district": i.district,
                "status": i.status,
            }
            for i in rows
        ]
    )


@router.post("/intersections")
def create_intersection(
    body: IntersectionIn, request: Request, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = Intersection(**body.model_dump())
    db.add(item)
    db.flush()
    log_op(db, request, _, "新增", f"新增路口：{item.name}")
    db.commit()
    return ok({"id": item.id}, "创建成功")


@router.put("/intersections/{item_id}")
def update_intersection(
    item_id: int, body: IntersectionIn, request: Request, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = db.query(Intersection).filter(Intersection.id == item_id, Intersection.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    for field, value in body.model_dump().items():
        setattr(item, field, value)
    log_op(db, request, _, "修改", f"修改路口：{item.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/intersections/{item_id}")
def delete_intersection(
    item_id: int, request: Request, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    item = db.query(Intersection).filter(Intersection.id == item_id, Intersection.is_deleted == 0).first()
    if item is None:
        raise BizError(*E_NOT_FOUND)
    item.is_deleted = 1
    log_op(db, request, _, "删除", f"删除路口：{item.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


# ---------------- 信号配时方案 ----------------
@router.get("/signal-plans")
def list_signal_plans(
    intersection_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer")),
):
    query = db.query(SignalPlan).filter(SignalPlan.is_deleted == 0)
    if intersection_id:
        query = query.filter(SignalPlan.intersection_id == intersection_id)
    rows = query.order_by(SignalPlan.intersection_id, SignalPlan.id).all()
    names = {i.id: i.name for i in db.query(Intersection).filter(Intersection.is_deleted == 0).all()}
    return ok(
        [
            {
                "id": p.id,
                "intersection_id": p.intersection_id,
                "intersection_name": names.get(p.intersection_id, ""),
                "name": p.name,
                "mode": p.mode,
                "cycle_seconds": p.cycle_seconds,
                "phase_count": p.phase_count,
                "phases": p.phases or [],
                "green_ratio": float(p.green_ratio),
                "is_active": p.is_active,
            }
            for p in rows
        ]
    )


def _deactivate_others(db: Session, intersection_id: int, keep_id: int | None = None):
    query = db.query(SignalPlan).filter(
        SignalPlan.intersection_id == intersection_id,
        SignalPlan.is_deleted == 0,
        SignalPlan.is_active == 1,
    )
    if keep_id:
        query = query.filter(SignalPlan.id != keep_id)
    query.update({SignalPlan.is_active: 0}, synchronize_session=False)


@router.post("/signal-plans")
def create_signal_plan(
    body: SignalPlanIn, request: Request, current_user: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    if not db.query(Intersection).filter(Intersection.id == body.intersection_id, Intersection.is_deleted == 0).first():
        raise BizError(*E_NOT_FOUND)
    plan = SignalPlan(
        intersection_id=body.intersection_id,
        name=body.name,
        mode=body.mode,
        cycle_seconds=body.cycle_seconds,
        phase_count=body.phase_count,
        phases=body.phases,
        green_ratio=round(
            sum(int(p.get("green", 0)) for p in (body.phases or [])) / max(1, body.cycle_seconds), 4
        ),
        is_active=1 if body.is_active else 0,
        created_by=current_user.id,
    )
    db.add(plan)
    db.flush()
    if body.is_active:
        _deactivate_others(db, body.intersection_id, keep_id=plan.id)
    log_op(db, request, current_user, "新增", f"新增配时方案：{plan.name}")
    db.commit()
    return ok({"id": plan.id}, "创建成功")


@router.put("/signal-plans/{item_id}")
def update_signal_plan(
    item_id: int, body: SignalPlanIn, request: Request, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    plan = db.query(SignalPlan).filter(SignalPlan.id == item_id, SignalPlan.is_deleted == 0).first()
    if plan is None:
        raise BizError(*E_NOT_FOUND)
    data = body.model_dump()
    plan.intersection_id = data["intersection_id"]
    plan.name = data["name"]
    plan.mode = data["mode"]
    plan.cycle_seconds = data["cycle_seconds"]
    plan.phase_count = data["phase_count"]
    plan.phases = data["phases"]
    plan.green_ratio = round(
        sum(int(p.get("green", 0)) for p in (data["phases"] or [])) / max(1, data["cycle_seconds"]), 4
    )
    if data["is_active"]:
        _deactivate_others(db, data["intersection_id"], keep_id=plan.id)
        plan.is_active = 1
    log_op(db, request, _, "修改", f"修改配时方案：{plan.name}")
    db.commit()
    return ok(None, "更新成功")


@router.delete("/signal-plans/{item_id}")
def delete_signal_plan(
    item_id: int, request: Request, _: User = Depends(require_roles("admin")), db: Session = Depends(get_db)
):
    plan = db.query(SignalPlan).filter(SignalPlan.id == item_id, SignalPlan.is_deleted == 0).first()
    if plan is None:
        raise BizError(*E_NOT_FOUND)
    plan.is_deleted = 1
    log_op(db, request, _, "删除", f"删除配时方案：{plan.name}（软删除）")
    db.commit()
    return ok(None, "删除成功")


@router.post("/signal-plans/calc")
def calc_signal_plan(
    body: WebsterCalcIn,
    current_user: User = Depends(require_roles("admin", "officer")),
):
    """Webster 配时计算（纯函数，不落库）：输入各相位流量与车道数，输出周期与绿灯时长"""
    result = webster_calc([p.model_dump() for p in body.phases])
    return ok(result, "计算完成" if not result["oversaturated"] else "交叉口已过饱和，按上限周期输出")


# ---------------- 信号灯实时状态 ----------------
@router.get("/signal-status")
def list_signal_status(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin", "officer", "user"))):
    """信号灯实时状态（大屏轮询用，所有登录角色可见）"""
    rows = (
        db.query(SignalStatus, Intersection)
        .join(Intersection, Intersection.id == SignalStatus.intersection_id)
        .filter(SignalStatus.is_deleted == 0, Intersection.is_deleted == 0)
        .all()
    )
    return ok(
        [
            {
                "intersection_id": s.intersection_id,
                "intersection_name": i.name,
                "current_phase": s.current_phase,
                "remaining_seconds": s.remaining_seconds,
                "mode": s.mode,
                "cycle_seconds": s.cycle_seconds,
                "updated_at": s.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for s, i in rows
        ]
    )
