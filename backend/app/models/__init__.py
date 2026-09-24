"""全部 ORM 模型（与 sql/init.sql 一一对应）

约定：所有表含 id/created_at/updated_at，软删除 is_deleted；
时间字段一律 DATETIME 本地时间（Asia/Shanghai），禁止 UTC 混用。
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class SoftDeleteMixin:
    is_deleted: Mapped[int] = mapped_column(default=0, comment="软删除：1已删")


# ============ 用户与权限 ============
class Role(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "role"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, comment="角色编码")
    name: Mapped[str] = mapped_column(String(64), comment="角色名称")
    description: Mapped[str] = mapped_column(String(255), default="", comment="角色描述")


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, comment="登录名")
    password_hash: Mapped[str] = mapped_column(String(128), comment="bcrypt 密码哈希")
    real_name: Mapped[str] = mapped_column(String(64), default="", comment="姓名")
    phone: Mapped[str] = mapped_column(String(20), default="", comment="手机号")
    email: Mapped[str] = mapped_column(String(128), default="", comment="邮箱")
    status: Mapped[int] = mapped_column(default=1, comment="1启用 0禁用")


class Menu(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "menu"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int] = mapped_column(default=0, comment="父菜单 id，0=顶级")
    name: Mapped[str] = mapped_column(String(64), comment="菜单名称")
    path: Mapped[str] = mapped_column(String(128), default="", comment="前端路由路径")
    component: Mapped[str] = mapped_column(String(128), default="", comment="前端组件路径")
    icon: Mapped[str] = mapped_column(String(64), default="", comment="图标名")
    menu_type: Mapped[int] = mapped_column(default=1, comment="1菜单 0目录")
    sort_order: Mapped[int] = mapped_column(default=0, comment="排序号")
    visible: Mapped[int] = mapped_column(default=1, comment="1显示 0隐藏")


class UserRole(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user_role"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(comment="用户 id")
    role_id: Mapped[int] = mapped_column(comment="角色 id")


class RoleMenu(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "role_menu"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(comment="角色 id")
    menu_id: Mapped[int] = mapped_column(comment="菜单 id")


class OpLog(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "op_log"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True, comment="操作人用户 id")
    username: Mapped[str] = mapped_column(String(64), default="", comment="操作人用户名")
    action: Mapped[str] = mapped_column(String(64), comment="操作类型")
    detail: Mapped[str] = mapped_column(String(512), default="", comment="操作详情")
    ip: Mapped[str] = mapped_column(String(64), default="", comment="来源 IP")


# ============ 交通业务 ============
class Intersection(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "intersection"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), comment="路口名称")
    longitude: Mapped[float] = mapped_column(Numeric(10, 6), comment="经度")
    latitude: Mapped[float] = mapped_column(Numeric(10, 6), comment="纬度")
    lane_count: Mapped[int] = mapped_column(default=4, comment="车道数")
    district: Mapped[str] = mapped_column(String(64), default="", comment="所属辖区")
    status: Mapped[int] = mapped_column(default=1, comment="1启用 0停用")


class SignalPlan(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "signal_plan"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intersection_id: Mapped[int] = mapped_column(comment="路口 id")
    name: Mapped[str] = mapped_column(String(64), comment="方案名称")
    mode: Mapped[str] = mapped_column(String(16), default="fixed", comment="fixed=定周期 adaptive=感应自适应")
    cycle_seconds: Mapped[int] = mapped_column(default=90, comment="周期时长（秒）")
    phase_count: Mapped[int] = mapped_column(default=4, comment="相位数")
    phases: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="相位配置")
    green_ratio: Mapped[float] = mapped_column(Numeric(5, 4), default=0.4, comment="绿信比")
    is_active: Mapped[int] = mapped_column(default=0, comment="1=当前启用方案")
    created_by: Mapped[int | None] = mapped_column(nullable=True, comment="创建人用户 id")


class SignalStatus(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "signal_status"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    intersection_id: Mapped[int] = mapped_column(unique=True, comment="路口 id")
    current_phase: Mapped[str] = mapped_column(String(64), default="", comment="当前相位名")
    remaining_seconds: Mapped[int] = mapped_column(default=0, comment="剩余秒数")
    mode: Mapped[str] = mapped_column(String(16), default="fixed", comment="当前模式")
    cycle_seconds: Mapped[int] = mapped_column(default=90, comment="当前周期（秒）")


class RoadSection(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "road_section"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), comment="路段名称")
    start_intersection_id: Mapped[int] = mapped_column(comment="起点路口 id")
    end_intersection_id: Mapped[int] = mapped_column(comment="终点路口 id")
    lane_count: Mapped[int] = mapped_column(default=4, comment="车道数")
    length_km: Mapped[float] = mapped_column(Numeric(6, 2), default=1.0, comment="长度（公里）")
    direction: Mapped[str] = mapped_column(String(16), default="东西", comment="走向")
    capacity: Mapped[int] = mapped_column(default=2400, comment="通行能力 pcu/h")


class TrafficFlow(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "traffic_flow"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    road_section_id: Mapped[int] = mapped_column(comment="路段 id")
    recorded_at: Mapped[datetime] = mapped_column(DateTime, comment="记录时间")
    flow: Mapped[int] = mapped_column(default=0, comment="折算小时流率 pcu/h")
    speed: Mapped[float] = mapped_column(Numeric(6, 2), default=0, comment="平均车速 km/h")
    saturation: Mapped[float] = mapped_column(Numeric(5, 3), default=0, comment="饱和度 v/c")
    congestion_level: Mapped[int] = mapped_column(default=0, comment="0自由流 1缓行 2拥堵 3严重拥堵")


# ============ 车辆与违章 ============
class Vehicle(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "vehicle"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True, comment="登记用户 id")
    plate_no: Mapped[str] = mapped_column(String(16), unique=True, comment="车牌号")
    vehicle_type: Mapped[str] = mapped_column(String(32), default="小型汽车", comment="车辆类型")
    color: Mapped[str] = mapped_column(String(16), default="", comment="车身颜色")
    owner_name: Mapped[str] = mapped_column(String(64), default="", comment="车主姓名")
    owner_phone: Mapped[str] = mapped_column(String(20), default="", comment="联系电话")


class Violation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "violation"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int | None] = mapped_column(nullable=True, comment="车辆 id")
    plate_no: Mapped[str] = mapped_column(String(16), comment="车牌号")
    intersection_id: Mapped[int | None] = mapped_column(nullable=True, comment="违章地点路口 id")
    violation_type: Mapped[str] = mapped_column(String(32), comment="违章类型")
    violation_time: Mapped[datetime] = mapped_column(DateTime, comment="违章时间")
    fine_amount: Mapped[float] = mapped_column(Numeric(8, 2), default=0, comment="罚款金额")
    deduct_points: Mapped[int] = mapped_column(default=0, comment="扣分")
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="待审核/已确认/已驳回/已处理")
    evidence_url: Mapped[str] = mapped_column(String(255), default="", comment="取证照片")
    audit_by: Mapped[int | None] = mapped_column(nullable=True, comment="审核人用户 id")
    audit_remark: Mapped[str] = mapped_column(String(255), default="", comment="审核备注")
    audit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    remark: Mapped[str] = mapped_column(String(255), default="", comment="备注")


# ============ 智慧停车 ============
class FeeRule(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "fee_rule"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), comment="规则名称")
    free_minutes: Mapped[int] = mapped_column(default=15, comment="免费时长（分钟）")
    first_hour_fee: Mapped[float] = mapped_column(Numeric(8, 2), default=5.0, comment="首小时费用")
    hourly_fee: Mapped[float] = mapped_column(Numeric(8, 2), default=3.0, comment="之后每小时费用")
    daily_cap: Mapped[float] = mapped_column(Numeric(8, 2), default=40.0, comment="单日封顶费用")


class ParkingLot(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parking_lot"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), comment="停车场名称")
    address: Mapped[str] = mapped_column(String(255), default="", comment="地址")
    total_slots: Mapped[int] = mapped_column(default=100, comment="车位总数")
    used_slots: Mapped[int] = mapped_column(default=0, comment="当前占用数")
    fee_rule_id: Mapped[int | None] = mapped_column(nullable=True, comment="计费规则 id")


class ParkingRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "parking_record"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parking_lot_id: Mapped[int] = mapped_column(comment="停车场 id")
    plate_no: Mapped[str] = mapped_column(String(16), comment="车牌号")
    enter_time: Mapped[datetime] = mapped_column(DateTime, comment="入场时间")
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="出场时间")
    fee: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True, comment="结算费用")
    status: Mapped[str] = mapped_column(String(16), default="inside", comment="inside在场/finished已出场")
    image_url: Mapped[str] = mapped_column(String(255), default="", comment="入场拍照")


# ============ 公共服务 ============
class Notice(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "notice"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(128), comment="公告标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="公告内容")
    publisher_id: Mapped[int | None] = mapped_column(nullable=True, comment="发布人用户 id")
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="发布时间")
    status: Mapped[int] = mapped_column(default=1, comment="1已发布 0已下架")


class Feedback(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(comment="提交用户 id")
    title: Mapped[str] = mapped_column(String(128), default="", comment="标题")
    content: Mapped[str] = mapped_column(Text, comment="反馈内容")
    reply: Mapped[str | None] = mapped_column(Text, nullable=True, comment="处理答复")
    status: Mapped[str] = mapped_column(String(16), default="pending", comment="pending/processing/resolved")
    handler_id: Mapped[int | None] = mapped_column(nullable=True, comment="受理人用户 id")
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="最近处理时间")
