"""管理端仪表盘：统计概览 + 最近操作日志"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_roles
from app.core.response import ok
from app.models import Feedback, OpLog, User, Vehicle, Violation
from app.models import ParkingLot as ParkingLotModel

router = APIRouter(prefix="/admin", tags=["系统仪表盘"])


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "officer")),
):
    day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    lots = db.query(ParkingLotModel).filter(ParkingLotModel.is_deleted == 0).all()
    total_slots = sum(lot.total_slots for lot in lots)
    used_slots = sum(lot.used_slots for lot in lots)
    return ok(
        {
            "user_count": int(db.query(func.count(User.id)).filter(User.is_deleted == 0).scalar() or 0),
            "vehicle_count": int(db.query(func.count(Vehicle.id)).filter(Vehicle.is_deleted == 0).scalar() or 0),
            "violation_today": int(
                db.query(func.count(Violation.id))
                .filter(Violation.is_deleted == 0, Violation.violation_time >= day_start)
                .scalar()
                or 0
            ),
            "violation_pending": int(
                db.query(func.count(Violation.id)).filter(Violation.is_deleted == 0, Violation.status == "pending").scalar() or 0
            ),
            "feedback_pending": int(
                db.query(func.count(Feedback.id))
                .filter(Feedback.is_deleted == 0, Feedback.status.in_(["pending", "processing"]))
                .scalar()
                or 0
            ),
            "parking_total": total_slots,
            "parking_used": used_slots,
            "parking_rate": round(used_slots / max(1, total_slots) * 100, 1),
        }
    )


@router.get("/recent-logs")
def recent_logs(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    rows = db.query(OpLog).filter(OpLog.is_deleted == 0).order_by(OpLog.id.desc()).limit(min(50, max(1, limit))).all()
    return ok(
        [
            {
                "id": r.id,
                "username": r.username,
                "action": r.action,
                "detail": r.detail,
                "ip": r.ip,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in rows
        ]
    )
