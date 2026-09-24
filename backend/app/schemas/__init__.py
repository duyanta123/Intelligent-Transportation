"""Pydantic 请求/响应模型（v2）"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---- 认证 ----
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    real_name: str = Field(default="", max_length=64)
    phone: str = Field(default="", max_length=20)


class LoginIn(BaseModel):
    # 显式限长：超长用户名打到 VARCHAR(64) 会触发数据库错误变 500
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    captcha_key: str = Field(min_length=8, max_length=64)
    captcha_code: str = Field(min_length=1, max_length=8)


class ProfileUpdateIn(BaseModel):
    real_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=128)


class PasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


# ---- 用户/角色/菜单 ----
class UserUpdateIn(BaseModel):
    real_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=128)
    status: int | None = Field(default=None, ge=0, le=1)


class RoleIn(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str = Field(max_length=64)
    description: str = Field(default="", max_length=255)


class MenuIn(BaseModel):
    parent_id: int = 0
    name: str = Field(max_length=64)
    path: str = Field(default="", max_length=128)
    component: str = Field(default="", max_length=128)
    icon: str = Field(default="", max_length=64)
    menu_type: int = 1
    sort_order: int = 0
    visible: int = 1


# ---- 路口与信号 ----
class IntersectionIn(BaseModel):
    name: str = Field(max_length=64)
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    lane_count: int = Field(default=4, ge=1, le=20)
    district: str = Field(default="", max_length=64)
    status: int = 1


class SignalPhaseIn(BaseModel):
    """配时方案的单相位：green 必须是可校验的整数（裸 dict 曾让 int("30.5") 直接 500）。

    extra="allow" 保留 yellow/allRed 等附加键，与既有数据结构兼容。
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(default="", max_length=64)
    green: int = Field(default=0, ge=0, le=600)


class SignalPlanIn(BaseModel):
    intersection_id: int
    name: str = Field(max_length=64)
    mode: str = Field(default="fixed", pattern=r"^(fixed|adaptive)$")
    cycle_seconds: int = Field(default=90, ge=40, le=180)
    phase_count: int = Field(default=4, ge=2, le=12)
    phases: list[SignalPhaseIn] | None = None
    is_active: bool = False


class WebsterPhaseIn(BaseModel):
    name: str = Field(default="", max_length=64)
    flow: float = Field(gt=0, description="关键车流量 pcu/h")
    lanes: int = Field(ge=1, le=12, description="该方向车道数")


class WebsterCalcIn(BaseModel):
    phases: list[WebsterPhaseIn] = Field(min_length=1, max_length=12)


# ---- 路况 ----
class RoadSectionIn(BaseModel):
    name: str = Field(max_length=64)
    start_intersection_id: int
    end_intersection_id: int
    lane_count: int = Field(default=4, ge=1, le=12)
    length_km: float = Field(default=1.0, gt=0, le=100)
    direction: str = Field(default="东西", max_length=16)


class FlowReportIn(BaseModel):
    road_section_id: int
    flow: int = Field(ge=0, le=2000, description="该分钟检测流量（辆）；上界防止折算后超出 INT 列范围")
    speed: float | None = Field(default=None, gt=0, le=200, description="实测平均车速 km/h")


# ---- 车辆与违章 ----
class VehicleIn(BaseModel):
    plate_no: str = Field(max_length=16)
    vehicle_type: str = Field(default="小型汽车", max_length=32)
    color: str = Field(default="", max_length=16)
    owner_name: str = Field(default="", max_length=64)
    owner_phone: str = Field(default="", max_length=20)
    user_id: int | None = None


class ViolationIn(BaseModel):
    plate_no: str = Field(max_length=16)
    intersection_id: int | None = None
    violation_type: str = Field(max_length=32)
    violation_time: datetime
    fine_amount: float = Field(default=0, ge=0, le=999999, description="上界与 Numeric(8,2) 列宽一致")
    deduct_points: int = Field(default=0, ge=0, le=12)
    evidence_url: str = Field(default="", max_length=255)
    remark: str = Field(default="", max_length=255)
    vehicle_id: int | None = None


class ViolationAuditIn(BaseModel):
    result: str = Field(pattern=r"^(confirmed|rejected)$", description="confirmed=通过 rejected=驳回")
    remark: str = Field(default="", max_length=255)


# ---- 停车 ----
class FeeRuleIn(BaseModel):
    name: str = Field(max_length=64)
    free_minutes: int = Field(ge=0, le=240)
    first_hour_fee: float = Field(ge=0, le=999999)
    hourly_fee: float = Field(ge=0, le=999999)
    daily_cap: float = Field(ge=0, le=999999)


class ParkingLotIn(BaseModel):
    name: str = Field(max_length=64)
    address: str = Field(default="", max_length=255)
    total_slots: int = Field(ge=1, le=10000)
    used_slots: int = Field(default=0, ge=0)
    fee_rule_id: int | None = None


class ParkingEnterIn(BaseModel):
    parking_lot_id: int
    plate_no: str = Field(max_length=16)


class ParkingExitIn(BaseModel):
    parking_lot_id: int
    plate_no: str = Field(max_length=16)


# ---- 公共服务 ----
class NoticeIn(BaseModel):
    title: str = Field(max_length=128)
    content: str = ""
    status: int = 1


class FeedbackIn(BaseModel):
    title: str = Field(default="", max_length=128)
    content: str = Field(min_length=5, max_length=2000)


class FeedbackHandleIn(BaseModel):
    status: str = Field(pattern=r"^(processing|resolved)$")
    reply: str = Field(min_length=2, max_length=1000)
