"""Pydantic 请求/响应模型（v2）"""
from datetime import datetime

from pydantic import BaseModel, Field


# ---- 认证 ----
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    real_name: str = Field(default="", max_length=64)
    phone: str = Field(default="", max_length=20)


class LoginIn(BaseModel):
    username: str
    password: str
    captcha_key: str
    captcha_code: str


class ProfileUpdateIn(BaseModel):
    real_name: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=128)


class PasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=64)


# ---- 用户/角色/菜单 ----
class UserUpdateIn(BaseModel):
    real_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: int | None = Field(default=None, ge=0, le=1)


class RoleIn(BaseModel):
    code: str = Field(min_length=2, max_length=32)
    name: str
    description: str = ""


class MenuIn(BaseModel):
    parent_id: int = 0
    name: str
    path: str = ""
    component: str = ""
    icon: str = ""
    menu_type: int = 1
    sort_order: int = 0
    visible: int = 1


# ---- 路口与信号 ----
class IntersectionIn(BaseModel):
    name: str
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    lane_count: int = Field(default=4, ge=1, le=20)
    district: str = ""
    status: int = 1


class SignalPlanIn(BaseModel):
    intersection_id: int
    name: str
    mode: str = Field(default="fixed", pattern=r"^(fixed|adaptive)$")
    cycle_seconds: int = Field(default=90, ge=40, le=180)
    phase_count: int = Field(default=4, ge=2, le=12)
    phases: list[dict] | None = None
    is_active: bool = False


class WebsterPhaseIn(BaseModel):
    name: str = ""
    flow: float = Field(gt=0, description="关键车流量 pcu/h")
    lanes: int = Field(ge=1, le=12, description="该方向车道数")


class WebsterCalcIn(BaseModel):
    phases: list[WebsterPhaseIn] = Field(min_length=1, max_length=12)


# ---- 路况 ----
class RoadSectionIn(BaseModel):
    name: str
    start_intersection_id: int
    end_intersection_id: int
    lane_count: int = Field(default=4, ge=1, le=12)
    length_km: float = Field(default=1.0, gt=0, le=100)
    direction: str = "东西"


class FlowReportIn(BaseModel):
    road_section_id: int
    flow: int = Field(ge=0, description="该分钟检测流量（辆）")
    speed: float | None = Field(default=None, gt=0, le=200, description="实测平均车速 km/h")


# ---- 车辆与违章 ----
class VehicleIn(BaseModel):
    plate_no: str
    vehicle_type: str = "小型汽车"
    color: str = ""
    owner_name: str = ""
    owner_phone: str = ""
    user_id: int | None = None


class ViolationIn(BaseModel):
    plate_no: str
    intersection_id: int | None = None
    violation_type: str
    violation_time: datetime
    fine_amount: float = Field(default=0, ge=0)
    deduct_points: int = Field(default=0, ge=0, le=12)
    evidence_url: str = ""
    remark: str = ""
    vehicle_id: int | None = None


class ViolationAuditIn(BaseModel):
    result: str = Field(pattern=r"^(confirmed|rejected)$", description="confirmed=通过 rejected=驳回")
    remark: str = ""


# ---- 停车 ----
class FeeRuleIn(BaseModel):
    name: str
    free_minutes: int = Field(ge=0, le=240)
    first_hour_fee: float = Field(ge=0)
    hourly_fee: float = Field(ge=0)
    daily_cap: float = Field(ge=0)


class ParkingLotIn(BaseModel):
    name: str
    address: str = ""
    total_slots: int = Field(ge=1, le=10000)
    used_slots: int = Field(default=0, ge=0)
    fee_rule_id: int | None = None


class ParkingEnterIn(BaseModel):
    parking_lot_id: int
    plate_no: str


class ParkingExitIn(BaseModel):
    parking_lot_id: int
    plate_no: str


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
