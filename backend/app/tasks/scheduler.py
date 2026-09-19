"""APScheduler 定时任务：模拟数据生成（.env 开关 MOCK_DATA_ENABLED 控制）

1. 每分钟：为全部路段生成一条分钟级流量记录（体现早晚高峰形态）
2. 每 10 秒：推进信号灯实时状态（按启用方案相位顺序轮转）
"""
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.algorithms import (
    congestion_level,
    hour_flow_rate,
    speed_by_saturation,
)

logger = logging.getLogger("smart-traffic.tasks")

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

# 信号灯相位推进时相位的黄灯/全红近似并入绿灯段处理（演示用途）
_phase_cursor: dict[int, int] = {}


def _mock_traffic_flow():
    """每分钟模拟上报：理论小时流率（附录 D.3 形态）折算为该分钟流量再落库"""
    from app.models import RoadSection, TrafficFlow

    db = SessionLocal()
    try:
        now = datetime.now()
        sections = db.query(RoadSection).filter(RoadSection.is_deleted == 0).all()
        weekday = now.weekday()
        hour = now.hour + now.minute / 60.0
        for section in sections:
            rate = hour_flow_rate(hour, section_factor=1.0, weekday=weekday)
            saturation = round(min(1.2, rate / max(1, section.capacity)), 3)
            db.add(
                TrafficFlow(
                    road_section_id=section.id,
                    recorded_at=now.replace(second=0, microsecond=0),
                    flow=int(rate),
                    speed=speed_by_saturation(55.0, saturation),
                    saturation=saturation,
                    congestion_level=congestion_level(saturation),
                )
            )
            # 记录真实检测到的分钟车辆数（供查询明细），流率列存折算值
            db.flush()
        db.commit()
        logger.info("流量模拟完成：%s 个路段", len(sections))
    except Exception:
        db.rollback()
        logger.exception("流量模拟任务失败")
    finally:
        db.close()


def _advance_signal_status():
    """每 10 秒推进信号灯：剩余秒数递减，归零后切换到下一相位"""
    from app.models import SignalPlan, SignalStatus

    db = SessionLocal()
    try:
        statuses = db.query(SignalStatus).filter(SignalStatus.is_deleted == 0).all()
        for status in statuses:
            plan = (
                db.query(SignalPlan)
                .filter(
                    SignalPlan.intersection_id == status.intersection_id,
                    SignalPlan.is_deleted == 0,
                    SignalPlan.is_active == 1,
                )
                .first()
            )
            phases = (plan.phases if plan else None) or []
            if not phases:
                continue
            remaining = status.remaining_seconds - 10
            if remaining > 0:
                status.remaining_seconds = remaining
                continue
            # 切换到下一相位
            names = [p.get("name", "") for p in phases]
            if status.current_phase in names:
                idx = (names.index(status.current_phase) + 1) % len(phases)
            else:
                idx = _phase_cursor.get(status.intersection_id, 0) % len(phases)
                _phase_cursor[status.intersection_id] = idx + 1
            nxt = phases[idx]
            status.current_phase = nxt.get("name", "")
            # 相位内剩余时间 = 绿灯 + 黄灯 + 全红（演示用简化）
            status.remaining_seconds = int(nxt.get("green", 30)) + int(nxt.get("yellow", 3)) + int(nxt.get("allRed", 1))
            if plan:
                status.mode = plan.mode
                status.cycle_seconds = plan.cycle_seconds
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("信号灯状态推进失败")
    finally:
        db.close()


def start_scheduler():
    if not settings.MOCK_DATA_ENABLED:
        logger.info("MOCK_DATA_ENABLED=false，模拟数据定时任务未启动")
        return
    scheduler.add_job(_mock_traffic_flow, "interval", seconds=60, id="mock_flow", replace_existing=True)
    scheduler.add_job(_advance_signal_status, "interval", seconds=10, id="signal_tick", replace_existing=True)
    scheduler.start()
    logger.info("模拟数据定时任务已启动（流量每 60 秒 / 信号灯每 10 秒）")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
