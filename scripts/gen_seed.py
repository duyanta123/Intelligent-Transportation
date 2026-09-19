# -*- coding: utf-8 -*-
"""
gen_seed.py —— 生成 sql/seed.sql（种子数据）

用法：在项目根目录执行  python scripts/gen_seed.py
说明：
  1. 输出为确定性数据（固定随机种子 20260920），重复生成结果一致
  2. 流量形态参数严格遵循《智慧交通-项目开发Prompt.md》附录 D.3：
     平峰基线 300-600 pcu/h；早晚高峰（7:30-9:00 / 17:30-19:00）峰值 1500-2200；
     夜间 23:00-5:00 为 50-150；全时段 ±10% 噪声；周五晚高峰 ×1.15；周末高峰 ×0.6
  3. 拥堵四级阈值（按饱和度 v/c）：自由流 <0.4，缓行 0.4-0.7，拥堵 0.7-0.9，严重拥堵 >=0.9
  4. 日期相对“当前时间”生成，覆盖最近 30 天；答辩前可重新生成以刷新日期
"""
import json
import math
import random
from datetime import datetime, timedelta

random.seed(20260920)

OUT_PATH = "sql/seed.sql"

# ---------- 通用常量 ----------
BCRYPT_HASH = "$2b$10$.8JMUD7yCn6peym6kynXO.EmF9bYlqNZG.dFd3b9fdaI.1v1C1Ywa"  # 密码 123456
CAPACITY_PER_LANE = 600  # 路段通行能力 pcu/h/车道（与后端 algorithms 模块一致）
PLATE_PREFIX = ["京A", "京B", "京C", "京Q", "冀A", "冀B"]
PLATE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
NOW = datetime.now()
TODAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)


def esc(v):
    """SQL 值转义：None->NULL，datetime->带引号时间，数字直出，字符串加引号"""
    if v is None:
        return "NULL"
    if isinstance(v, datetime):
        return dt(v)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if isinstance(v, float):
            return f"{v:.2f}"
        return str(v)
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'"


def dt(v):
    return "'" + v.strftime("%Y-%m-%d %H:%M:%S") + "'"


def rand_plate(nev=False):
    """生成车牌号：普通 5 位（共 7 字符）或新能源 8 位"""
    if nev:
        return random.choice(PLATE_PREFIX) + random.choice("DF") + "".join(
            random.choice(PLATE_LETTERS + "0123456789") for _ in range(5))
    return random.choice(PLATE_PREFIX) + "".join(
        random.choice(PLATE_LETTERS) for _ in range(2)) + "".join(
        random.choice("0123456789") for _ in range(3)) + random.choice(PLATE_LETTERS + "0123456789")


def congestion_level(sat):
    """按饱和度分级：0 自由流 / 1 缓行 / 2 拥堵 / 3 严重拥堵"""
    if sat < 0.4:
        return 0
    if sat < 0.7:
        return 1
    if sat < 0.9:
        return 2
    return 3


def speed_by_sat(base_speed, sat):
    """按饱和度推算平均车速（速度-饱和度经验曲线，与后端 algorithms 一致）"""
    return round(max(8.0, base_speed * max(0.12, 1.0 - 0.78 * sat ** 1.8)), 1)


def hour_flow(h, section_factor, weekday):
    """h 为小数小时；返回该时刻折算小时流率（附录 D.3 形态）"""
    if 23.0 <= h or h < 5.0:
        base = random.uniform(50, 150)
    else:
        base = random.uniform(300, 600)
    amp = 1700.0 * section_factor
    if weekday >= 5:  # 周末高峰弱化
        amp *= 0.6
    morning = amp * math.exp(-((h - 8.25) / 0.8) ** 2) if 5.0 <= h < 12.0 else 0.0
    evening = amp * math.exp(-((h - 18.25) / 0.8) ** 2) if 15.0 <= h < 22.0 else 0.0
    if weekday == 4:  # 周五晚高峰 ×1.15
        evening *= 1.15
    flow = (base + morning + evening) * section_factor * random.uniform(0.9, 1.1)
    return int(max(30, min(2400, flow)))


# ---------- 输出缓冲 ----------
lines = []
lines.append("-- ============================================================")
lines.append("-- seed.sql —— 种子数据（由 scripts/gen_seed.py 生成，请勿手改）")
lines.append(f"-- 生成时间：{NOW.strftime('%Y-%m-%d %H:%M:%S')}；数据相对当前时间覆盖最近 30 天")
lines.append("-- ============================================================")
lines.append("SET NAMES utf8mb4;")
lines.append("USE smart_traffic;")
lines.append("")


def insert(table, columns, rows, chunk=400):
    lines.append(f"-- {table} 种子数据（{len(rows)} 行）")
    for i in range(0, len(rows), chunk):
        part = rows[i:i + chunk]
        values = ",\n".join("(" + ", ".join(esc(c) for c in row) + ")" for row in part)
        lines.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n{values};")
    lines.append("")


NOW_STR = NOW  # 直接传 datetime 对象，由 esc() 统一转义

# ---------- 1. 角色 ----------
insert("role", ["id", "code", "name", "description", "created_at", "updated_at"], [
    (1, "admin", "管理员", "系统管理员，拥有全部权限", NOW_STR, NOW_STR),
    (2, "officer", "交警/运营人员", "交通业务录入、审核与处理", NOW_STR, NOW_STR),
    (3, "user", "普通用户", "市民用户，查询与提交反馈", NOW_STR, NOW_STR),
])

# ---------- 2. 用户 ----------
users = [
    (1, "admin", "系统管理员", "13800000001", "admin@smart-traffic.local"),
    (2, "officer", "王交警", "13800000002", "officer@smart-traffic.local"),
    (3, "user", "张市民", "13800000003", "user@smart-traffic.local"),
]
insert("user", ["id", "username", "password_hash", "real_name", "phone", "email", "status", "created_at", "updated_at"],
       [(i, u, BCRYPT_HASH, r, p, e, 1, NOW_STR, NOW_STR) for i, u, r, p, e in users])

insert("user_role", ["user_id", "role_id", "created_at", "updated_at"],
       [(1, 1, NOW_STR, NOW_STR), (2, 2, NOW_STR, NOW_STR), (3, 3, NOW_STR, NOW_STR)])

# ---------- 3. 菜单 ----------
menus = [
    (1, 0, "系统仪表盘", "/dashboard", "views/dashboard/index.vue", "Odometer", 1, 1),
    (2, 0, "数据可视化大屏", "/big-screen", "views/bigscreen/index.vue", "DataBoard", 1, 2),
    (3, 0, "交通管理", "", "", "Location", 0, 10),
    (4, 3, "路口管理", "/traffic/intersections", "views/traffic/intersections.vue", "OfficeBuilding", 1, 11),
    (5, 3, "信号配时", "/traffic/signal-plans", "views/traffic/signal-plans.vue", "Timer", 1, 12),
    (6, 0, "路况监测", "", "", "Guide", 0, 20),
    (7, 6, "路段管理", "/traffic/sections", "views/traffic/sections.vue", "Guide", 1, 21),
    (8, 6, "流量与拥堵", "/traffic/flow", "views/traffic/flow.vue", "TrendCharts", 1, 22),
    (9, 0, "车辆违章", "", "", "Warning", 0, 30),
    (10, 9, "车辆管理", "/vehicle/vehicles", "views/vehicle/vehicles.vue", "Van", 1, 31),
    (11, 9, "违章管理", "/vehicle/violations", "views/vehicle/violations.vue", "WarningFilled", 1, 32),
    (12, 0, "智慧停车", "", "", "House", 0, 40),
    (13, 12, "停车场管理", "/parking/lots", "views/parking/lots.vue", "House", 1, 41),
    (14, 12, "出入场记录", "/parking/records", "views/parking/records.vue", "Tickets", 1, 42),
    (15, 12, "计费规则", "/parking/fee-rules", "views/parking/fee-rules.vue", "Money", 1, 43),
    (16, 0, "智能工具", "", "", "Cpu", 0, 50),
    (17, 16, "车牌识别", "/tools/lpr", "views/tools/lpr.vue", "Camera", 1, 51),
    (18, 0, "公共服务", "", "", "ChatDotRound", 0, 60),
    (19, 18, "公告资讯", "/service/notices", "views/service/notices.vue", "Bell", 1, 61),
    (20, 18, "投诉反馈", "/service/feedback", "views/service/feedback.vue", "ChatLineSquare", 1, 62),
    (21, 0, "系统管理", "", "", "Setting", 0, 70),
    (22, 21, "用户管理", "/system/users", "views/system/users.vue", "User", 1, 71),
    (23, 21, "角色管理", "/system/roles", "views/system/roles.vue", "Avatar", 1, 72),
    (24, 21, "菜单管理", "/system/menus", "views/system/menus.vue", "Menu", 1, 73),
    (25, 21, "操作日志", "/system/logs", "views/system/logs.vue", "Document", 1, 74),
]
insert("menu", ["id", "parent_id", "name", "path", "component", "icon", "menu_type", "sort_order", "visible", "created_at", "updated_at"],
       [(mid, p, n, pa, c, ic, mt, so, 1, NOW_STR, NOW_STR) for mid, p, n, pa, c, ic, mt, so in menus])

admin_menus = [m[0] for m in menus]
officer_menus = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
user_menus = [2, 6, 7, 8, 9, 10, 11, 12, 13, 18, 19, 20]
role_menu_rows = []
for rid, mids in ((1, admin_menus), (2, officer_menus), (3, user_menus)):
    for mid in mids:
        role_menu_rows.append((rid, mid, NOW_STR, NOW_STR))
insert("role_menu", ["role_id", "menu_id", "created_at", "updated_at"], role_menu_rows)

# ---------- 4. 路口（附录 D.1 固定坐标） ----------
intersections = [
    (1, "中山路口", 116.407, 39.904, 4, "城东辖区"),
    (2, "解放路口", 116.418, 39.912, 6, "城东辖区"),
    (3, "建设路口", 116.395, 39.897, 4, "城西辖区"),
    (4, "和平路口", 116.429, 39.921, 4, "城北辖区"),
    (5, "人民路口", 116.382, 39.889, 4, "城南辖区"),
    (6, "朝阳路口", 116.441, 39.908, 6, "城东辖区"),
    (7, "新华路口", 116.410, 39.928, 4, "城北辖区"),
    (8, "友谊路口", 116.375, 39.905, 4, "城西辖区"),
]
insert("intersection", ["id", "name", "longitude", "latitude", "lane_count", "district", "status", "created_at", "updated_at"],
       [(i, n, lng, lat, ln, d, 1, NOW_STR, NOW_STR) for i, n, lng, lat, ln, d in intersections])

# ---------- 5. 信号配时方案 + 实时状态 ----------
PHASE_NAMES = ["南北直行", "南北左转", "东西直行", "东西左转"]
PHASE_RATIO = [0.3, 0.2, 0.3, 0.2]
plan_rows, status_rows = [], []
plan_id = 0
for iid, name, lng, lat, lanes, district in intersections:
    adaptive = iid in (1, 2, 6)  # 三个重点路口启用感应自适应
    cycle_target = random.choice([80, 90, 100, 110])
    green_total = cycle_target - 4 * 4  # 每相位损失=黄灯3s+全红1s
    phases = []
    for k, pn in enumerate(PHASE_NAMES):
        g = int(round(green_total * PHASE_RATIO[k] / sum(PHASE_RATIO)))
        phases.append({"name": pn, "green": max(15, g), "yellow": 3, "allRed": 1})
    real_cycle = sum(p["green"] + p["yellow"] + p["allRed"] for p in phases)
    green_ratio = round(sum(p["green"] for p in phases) / real_cycle, 4)
    plan_id += 1
    plan_rows.append((plan_id, iid, f"{name}-定周期方案", "fixed", real_cycle, 4,
                      json.dumps(phases, ensure_ascii=False), green_ratio, 0 if adaptive else 1, 1, NOW_STR, NOW_STR))
    if adaptive:
        plan_id += 1
        ad_phases = [dict(p) for p in phases]
        for p in ad_phases:
            p["green"] = min(60, int(p["green"] * 1.1))
        ad_cycle = sum(p["green"] + p["yellow"] + p["allRed"] for p in ad_phases)
        plan_rows.append((plan_id, iid, f"{name}-感应自适应方案", "adaptive", ad_cycle, 4,
                          json.dumps(ad_phases, ensure_ascii=False), round(sum(p["green"] for p in ad_phases) / ad_cycle, 4),
                          1, 1, NOW_STR, NOW_STR))
        cur_mode, cur_cycle, ph = "adaptive", ad_cycle, ad_phases
    else:
        cur_mode, cur_cycle, ph = "fixed", real_cycle, phases
    cur = random.choice(ph)
    status_rows.append((iid, cur["name"], random.randint(5, cur["green"]), cur_mode, cur_cycle, NOW_STR, NOW_STR))

lines.append("-- signal_plan 种子数据（{} 行）".format(len(plan_rows)))
for row in plan_rows:
    vals = ", ".join(esc(v) for v in row)
    lines.append(f"INSERT INTO signal_plan (id, intersection_id, name, mode, cycle_seconds, phase_count, phases, green_ratio, is_active, created_by, created_at, updated_at) VALUES ({vals});")
lines.append("")
insert("signal_status",
       ["intersection_id", "current_phase", "remaining_seconds", "mode", "cycle_seconds", "updated_at", "created_at"],
       status_rows)

# ---------- 6. 路段（20 条） ----------
sections_spec = [
    ("中山路东段", 1, 2, 4, 1.80, "东西"), ("中山路西段", 8, 1, 2, 2.60, "东西"),
    ("解放路北段", 2, 4, 6, 1.20, "南北"), ("解放路南段", 3, 2, 4, 1.50, "南北"),
    ("建设路东段", 3, 1, 4, 1.10, "东西"), ("建设路南段", 5, 3, 2, 2.20, "南北"),
    ("和平路东段", 4, 6, 4, 1.60, "东西"), ("和平路西段", 7, 4, 2, 1.40, "东西"),
    ("人民路东段", 5, 8, 4, 1.90, "东西"), ("人民路北段", 3, 5, 4, 1.30, "南北"),
    ("朝阳路北段", 6, 7, 6, 1.70, "南北"), ("朝阳路南段", 2, 6, 4, 2.10, "南北"),
    ("新华路东段", 7, 4, 4, 0.90, "东西"), ("新华路西段", 8, 7, 2, 2.80, "东西"),
    ("友谊路北段", 8, 3, 4, 1.00, "南北"), ("友谊路南段", 5, 8, 2, 1.20, "南北"),
    ("中山解放联络线", 1, 2, 2, 0.60, "南北"), ("建设和平联络线", 3, 4, 2, 2.40, "东西"),
    ("人民朝阳联络线", 5, 6, 2, 3.20, "东西"), ("新华友谊联络线", 7, 8, 2, 1.80, "东西"),
]
section_rows = []
for sid, (name, s, e, lanes, length, direction) in enumerate(sections_spec, start=1):
    section_rows.append((sid, name, s, e, lanes, length, direction, lanes * CAPACITY_PER_LANE, NOW_STR, NOW_STR))
insert("road_section",
       ["id", "name", "start_intersection_id", "end_intersection_id", "lane_count", "length_km", "direction", "capacity", "created_at", "updated_at"],
       section_rows)

# ---------- 7. 流量数据（20 路段 × 最近 30 天，小时粒度，含今日至当前小时） ----------
flow_rows = []
start_day = TODAY - timedelta(days=29)
section_factors = {sid: random.uniform(0.85, 1.15) for sid in range(1, 21)}
base_speeds = {sid: random.uniform(48, 58) for sid in range(1, 21)}
for day_offset in range(30):
    day = start_day + timedelta(days=day_offset)
    weekday = day.weekday()
    last_hour = NOW.hour if day == TODAY else 23
    for hour in range(0, last_hour + 1):
        ts = day.replace(hour=hour)
        for sid in range(1, 21):
            lanes = sections_spec[sid - 1][3]
            capacity = lanes * CAPACITY_PER_LANE
            flow = hour_flow(hour + random.choice([0.0]), section_factors[sid], weekday)
            sat = round(min(1.2, flow / capacity), 3)
            speed = speed_by_sat(base_speeds[sid], sat)
            flow_rows.append((sid, ts, flow, speed, sat, congestion_level(sat)))
lines.append(f"-- traffic_flow 种子数据（{len(flow_rows)} 行，小时粒度）")
CHUNK = 300
for i in range(0, len(flow_rows), CHUNK):
    part = flow_rows[i:i + CHUNK]
    values = ",\n".join(
        "(" + ", ".join(esc(c) for c in (r[0], r[1], r[2], r[3], r[4], r[5], 0, r[1], r[1])) + ")" for r in part)
    lines.append(f"INSERT INTO traffic_flow (road_section_id, recorded_at, flow, speed, saturation, congestion_level, is_deleted, created_at, updated_at) VALUES\n{values};")
lines.append("")

# ---------- 8. 车辆 ----------
vehicles = []
plate_pool = []
for i in range(1, 16):
    nev = i % 5 == 0  # 每 5 辆 1 台新能源（8 位牌）
    plate = rand_plate(nev)
    while plate in plate_pool:
        plate = rand_plate(nev)
    plate_pool.append(plate)
    owner_user = 3 if i <= 6 else None
    vehicles.append((i, owner_user, plate, random.choice(["小型汽车", "小型新能源汽车", "小型汽车"]),
                     random.choice(["白色", "黑色", "银色", "蓝色", "红色"]),
                     random.choice(["张伟", "李娜", "王强", "赵敏", "刘洋", "陈静", "杨帆", "周杰", "吴迪", "郑爽", "孙磊", "马丽", "朱婷", "胡军", "高翔"]),
                     f"139{random.randint(10000000, 99999999)}"))
insert("vehicle", ["id", "user_id", "plate_no", "vehicle_type", "color", "owner_name", "owner_phone", "created_at", "updated_at"],
       [(i, u, p, t, c, o, ph, NOW_STR, NOW_STR) for i, u, p, t, c, o, ph in vehicles])

# ---------- 9. 违章（500+） ----------
extra_plates = []
for _ in range(25):
    p = rand_plate(random.random() < 0.25)
    while p in plate_pool + extra_plates:
        p = rand_plate()
    extra_plates.append(p)
all_plates = plate_pool + extra_plates
violation_types = [("闯红灯", 200, 6), ("超速", 200, 3), ("违停", 150, 0), ("不按导向车道行驶", 100, 2)]
violation_rows = []
v_time_base = TODAY - timedelta(days=30)
for i in range(1, 521):
    vtype, fine, points = random.choice(violation_types)
    v_time = v_time_base + timedelta(
        minutes=random.randint(0, int((NOW - v_time_base).total_seconds() / 60)))
    plate = random.choice(all_plates)
    vid = next((v[0] for v in vehicles if v[2] == plate), None)
    r = random.random()
    if r < 0.55:
        status, audit_by, audit_remark, audit_time, remark = "processed", 2, "证据清晰，罚款已缴纳，扣分已执行", v_time + timedelta(hours=random.randint(6, 72)), "已处理完毕"
    elif r < 0.80:
        status, audit_by, audit_remark, audit_time, remark = "confirmed", 2, "审核通过，等待当事人处理", v_time + timedelta(hours=random.randint(2, 48)), ""
    elif r < 0.92:
        status, audit_by, audit_remark, audit_time, remark = "pending", None, "", None, ""
    else:
        status, audit_by, audit_remark, audit_time, remark = "rejected", 2, "证据不足或照片模糊，予以驳回", v_time + timedelta(hours=random.randint(2, 48)), ""
    violation_rows.append((i, vid, plate, random.randint(1, 8), vtype, v_time, fine, points, status, "",
                           audit_by, audit_remark, audit_time, remark))
lines.append(f"-- violation 种子数据（{len(violation_rows)} 行）")
for i in range(0, len(violation_rows), 200):
    part = violation_rows[i:i + 200]
    values = ",\n".join("(" + ", ".join(esc(c) for c in row) + ")" for row in part)
    lines.append(f"INSERT INTO violation (id, vehicle_id, plate_no, intersection_id, violation_type, violation_time, fine_amount, deduct_points, status, evidence_url, audit_by, audit_remark, audit_time, remark) VALUES\n{values};")
lines.append("")

# ---------- 10. 计费规则 + 停车场 ----------
insert("fee_rule", ["id", "name", "free_minutes", "first_hour_fee", "hourly_fee", "daily_cap", "created_at", "updated_at"], [
    (1, "路内停车标准", 15, 5.00, 3.00, 40.00, NOW_STR, NOW_STR),
    (2, "商圈停车标准", 30, 8.00, 5.00, 60.00, NOW_STR, NOW_STR),
])
lots = [(1, "市政广场地下停车场", "城东区中山路 1 号地下", 200, 143, 1),
        (2, "万达广场停车场", "城东区朝阳路 88 号", 300, 236, 2)]
insert("parking_lot", ["id", "name", "address", "total_slots", "used_slots", "fee_rule_id", "created_at", "updated_at"],
       [(i, n, a, t, u, f, NOW_STR, NOW_STR) for i, n, a, t, u, f in lots])


# 计费函数（与后端 app/services/algorithms.py 中 compute_parking_fee 保持一致）
def compute_parking_fee(enter, exit_time, free_minutes, first_hour_fee, hourly_fee, daily_cap):
    import math as _m
    total_minutes = (exit_time - enter).total_seconds() / 60.0
    if total_minutes <= 0:
        return 0.0
    full_days = int(total_minutes // 1440)
    remainder = total_minutes - full_days * 1440
    fee = full_days * float(daily_cap)
    if remainder > free_minutes:
        billable_hours = _m.ceil((remainder - free_minutes) / 60.0)
        fee += min(float(first_hour_fee) + (billable_hours - 1) * float(hourly_fee), float(daily_cap))
    return round(fee, 2)


# ---------- 11. 出入场记录（300 条，其中约 30 条在场） ----------
record_rows = []
enter_base = TODAY - timedelta(days=14)
inside_count = 0
for i in range(1, 301):
    lot = random.choice(lots)
    rule_id = lot[5]
    free_minutes, first_hour_fee, hourly_fee, daily_cap = (15, 5.0, 3.0, 40.0) if rule_id == 1 else (30, 8.0, 5.0, 60.0)
    enter = enter_base + timedelta(minutes=random.randint(0, int((NOW - enter_base).total_seconds() / 60)))
    is_inside = (i % 10 == 0) and inside_count < 30 and (NOW - enter) < timedelta(hours=8)
    if is_inside:
        inside_count += 1
        record_rows.append((i, lot[0], random.choice(all_plates[:20]), enter, None, None, "inside", "", NOW_STR, NOW_STR))
    else:
        duration_min = random.choice([random.randint(10, 60), random.randint(60, 300), random.randint(300, 1500)])
        exit_time = min(enter + timedelta(minutes=duration_min), NOW)
        fee = compute_parking_fee(enter, exit_time, free_minutes, first_hour_fee, hourly_fee, daily_cap)
        record_rows.append((i, lot[0], random.choice(all_plates[:20]), enter, exit_time, fee, "finished", "", NOW_STR, NOW_STR))
used = {1: sum(1 for r in record_rows if r[1] == 1 and r[6] == "inside"),
        2: sum(1 for r in record_rows if r[1] == 2 and r[6] == "inside")}
lines.append(f"-- parking_record 种子数据（{len(record_rows)} 行）")
for i in range(0, len(record_rows), 200):
    part = record_rows[i:i + 200]
    values = ",\n".join("(" + ", ".join(esc(c) for c in row) + ")" for row in part)
    lines.append(f"INSERT INTO parking_record (id, parking_lot_id, plate_no, enter_time, exit_time, fee, status, image_url, created_at, updated_at) VALUES\n{values};")
lines.append("")
# 以在场记录数校正停车场占用
lines.append(f"UPDATE parking_lot SET used_slots = {max(used[1], 120)} WHERE id = 1;")
lines.append(f"UPDATE parking_lot SET used_slots = {max(used[2], 200)} WHERE id = 2;")
lines.append("")

# ---------- 12. 公告 ----------
notices = [
    ("关于中山路口信号灯配时优化调整的公告", "为缓解早高峰拥堵，自本月起中山路口启用感应自适应配时方案，早晚高峰周期将在 80-120 秒间动态调整，请广大驾驶人按信号灯指示通行。"),
    ("城东区新增两处违停严管路段", "即日起，朝阳路北段、新华路东段列为违停严管路段，违停车辆将被依法抓拍处罚，请规范停车。"),
    ("市政广场地下停车场收费调整通知", "市政广场地下停车场自下月 1 日起执行新计费标准：免费时长 15 分钟，首小时 5 元，之后每小时 3 元，单日封顶 40 元。"),
    ("智慧交通平台上线公告", "智慧交通综合管理服务平台正式上线，市民用户可查询路况、违章与停车场信息，欢迎体验并提交反馈。"),
    ("周五晚高峰出行提示", "本周五晚高峰预计流量上升约 15%，建议错峰出行或选择公共交通，实时路况请查看平台数据大屏。"),
]
notice_rows = []
for i, (title, content) in enumerate(notices, start=1):
    published = NOW - timedelta(days=(6 - i) * 3, hours=random.randint(1, 10))
    notice_rows.append((i, title, content, 1, published, 1))
insert("notice", ["id", "title", "content", "publisher_id", "published_at", "status", "created_at", "updated_at"],
       [(r[0], r[1], r[2], r[3], r[4], r[5], NOW_STR, NOW_STR) for r in notice_rows])

# ---------- 13. 投诉反馈 ----------
feedbacks = [
    (3, "中山路口早高峰绿灯太短", "中山路口早高峰南北方向绿灯只有 20 秒，行人来不及过街，希望调整配时。", "已转信号配时部门核查，将于本周内优化。", "resolved"),
    (3, "万达广场停车场出口拥堵", "晚高峰万达停车场出口排队严重，建议增开出出口通道。", "已协调物业增开临时出口。", "resolved"),
    (3, "人民路口行人信号灯损坏", "人民路口东北角行人信号灯不亮，存在安全隐患。", None, "processing"),
    (3, "新华路东段夜间大货车噪音", "夜间有大量大货车通行，噪音扰民，建议限行。", None, "pending"),
    (3, "建议增加共享单车停放区", "地铁站周边共享单车乱停放，建议划定专门停放区。", None, "pending"),
    (3, "建设路口标线不清晰", "建设路口左转导向标线磨损严重，雨天难以辨认。", None, "pending"),
    (3, "市政停车场充电桩不足", "新能源车越来越多，希望增加充电桩数量。", None, "pending"),
    (3, "朝阳路口放学时段拥堵", "朝阳路口 17:00-18:00 接送孩子车辆集中，拥堵严重。", "已安排高峰期警力疏导。", "resolved"),
    (3, "反馈平台操作问题", "违章查询页面偶尔加载很慢。", None, "processing"),
    (3, "解放路口摄像头补光过亮", "夜间补光灯太亮影响驾驶视线，建议调整角度。", None, "pending"),
    (3, "建议开通路况微信推送", "希望支持微信订阅路况推送。", None, "pending"),
    (3, "表扬交警同志", "和平路口执勤交警帮助老人过马路，特此表扬。", "感谢您的肯定，已转达。", "resolved"),
]
fb_rows = []
for i, (uid, title, content, reply, status) in enumerate(feedbacks, start=1):
    created = NOW - timedelta(days=random.randint(1, 25), hours=random.randint(0, 20))
    handler = 2 if reply else None
    handled_at = created + timedelta(hours=random.randint(4, 60)) if reply else None
    fb_rows.append((i, uid, title, content, reply, status, handler, handled_at))
insert("feedback", ["id", "user_id", "title", "content", "reply", "status", "handler_id", "handled_at", "created_at", "updated_at"],
       [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], NOW_STR, NOW_STR) for r in fb_rows])

# ---------- 14. 操作日志 ----------
op_samples = [
    ("登录", "用户登录成功"), ("审核", "审核违章记录"), ("新增", "新增路口信息"), ("修改", "调整信号配时方案"),
    ("发布", "发布公告通知"), ("受理", "受理投诉反馈"), ("删除", "删除车辆信息（软删除）"), ("计算", "执行 Webster 配时计算"),
]
op_rows = []
for i in range(1, 31):
    uid = random.choice([1, 2, 2, 2, 3])
    username = {1: "admin", 2: "officer", 3: "user"}[uid]
    action, detail = random.choice(op_samples)
    created = NOW - timedelta(minutes=random.randint(5, 60 * 24 * 3))
    op_rows.append((i, uid, username, action, f"{detail}", f"127.0.0.1", created))
lines.append(f"-- op_log 种子数据（{len(op_rows)} 行）")
for i in range(0, len(op_rows), 200):
    part = op_rows[i:i + 200]
    values = ",\n".join(
        "(" + ", ".join(esc(c) for c in (r[0], r[1], r[2], r[3], r[4], r[5], 0, r[6], r[6])) + ")"
        for r in part)
    lines.append(f"INSERT INTO op_log (id, user_id, username, action, detail, ip, is_deleted, created_at, updated_at) VALUES\n{values};")
lines.append("")

# ---------- 写出文件 ----------
with open(OUT_PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write("\n".join(lines))

import os
size_kb = os.path.getsize(OUT_PATH) / 1024
print(f"已生成 {OUT_PATH}：{size_kb:.0f} KB")
print(f"  流量数据 {len(flow_rows)} 行；违章 {len(violation_rows)} 行；出入场 {len(record_rows)} 行")
