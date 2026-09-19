"""核心算法模块（纯函数，不碰数据库）——课程答辩亮点

包含三组算法，参数统一遵循《智慧交通-项目开发Prompt.md》附录 D：
  1. Webster 信号配时计算（附录 D.2）
  2. 拥堵四级分级（附录 D.3：按饱和度 v/c）
  3. 停车分时段计费（免费时长/首小时/每小时/单日封顶）
"""
import math

# ---- Webster 参数（附录 D.2，禁止另行设定） ----
SATURATION_FLOW = 1800.0      # 饱和流量 s：pcu/h/车道
LOSS_PER_PHASE = 6.0          # 每相位损失 = 启动损失 3s + 黄灯 3s（含全红 1s）
CYCLE_MIN, CYCLE_MAX = 40, 180
MIN_GREEN = 15                # 最短绿灯秒数

# ---- 拥堵分级阈值（按饱和度 v/c，附录 D.3） ----
CONGESTION_THRESHOLDS = (0.4, 0.7, 0.9)

# ---- 路段通行能力（pcu/h/车道），用于流量饱和度计算 ----
CAPACITY_PER_LANE = 600.0


def webster_calc(phases: list[dict]) -> dict:
    """按 Webster 公式估算最优周期与各相位绿灯时长。

    入参 phases：[{"name": 相位名, "flow": 关键车流量 pcu/h, "lanes": 该方向车道数}]
    出参：{"cycle_seconds", "phases": [{"name", "green", "y"}], "total_lost", "y_sum", "oversaturated"}

    公式：y_i = q_i/(s×n_i)；Y = Σy_i；L = Σ每相位损失；
          C0 = (1.5L+5)/(1-Y)，钳制 [40,180]；绿灯按 y_i/Y 分配，最短 15s。
    """
    if not phases:
        raise ValueError("至少需要一个相位")
    if len(phases) > 12:
        raise ValueError("相位数量过多")
    y_list: list[float] = []
    for p in phases:
        flow = float(p.get("flow", 0))
        lanes = int(p.get("lanes", 1))
        if flow <= 0:
            raise ValueError(f"相位[{p.get('name', '')}]车流量必须大于 0")
        if lanes <= 0:
            raise ValueError(f"相位[{p.get('name', '')}]车道数必须大于 0")
        y_list.append(flow / (SATURATION_FLOW * lanes))

    y_sum = sum(y_list)
    total_lost = len(phases) * LOSS_PER_PHASE
    oversaturated = y_sum >= 0.95
    if oversaturated:
        cycle = float(CYCLE_MAX)  # 过饱和按上限周期处理
    else:
        cycle = (1.5 * total_lost + 5) / (1 - y_sum)
        cycle = max(float(CYCLE_MIN), min(float(CYCLE_MAX), cycle))

    green_available = cycle - total_lost
    if green_available < MIN_GREEN * len(phases):
        # 周期扣除损失后不足以满足最短绿灯，按最短绿灯下限输出
        greens = [float(MIN_GREEN)] * len(phases)
    else:
        greens = [green_available * y / y_sum for y in y_list]
        # 最短绿灯 15s 约束：不足者补足，差额按比例从其他相位扣减
        for _ in range(10):
            low = [i for i, g in enumerate(greens) if g < MIN_GREEN - 1e-9]
            if not low:
                break
            deficit = sum(MIN_GREEN - greens[i] for i in low)
            for i in low:
                greens[i] = float(MIN_GREEN)
            high = [i for i in range(len(greens)) if i not in low]
            high_total = sum(greens[i] for i in high)
            if not high or high_total <= 0:
                break
            for i in high:
                greens[i] -= deficit * greens[i] / high_total

    greens = [max(MIN_GREEN, round(g)) for g in greens]
    # 取整可能使总绿灯超出钳制周期：从最大相位逐步扣减（不低于最短绿灯）
    limit = int(min(CYCLE_MAX, cycle)) - int(total_lost)
    while sum(greens) > limit:
        idx_max = greens.index(max(greens))
        if greens[idx_max] <= MIN_GREEN:
            break
        greens[idx_max] -= 1
    result_phases = [
        {"name": phases[i].get("name", f"相位{i + 1}"), "green": greens[i], "y": round(y_list[i], 4)}
        for i in range(len(phases))
    ]
    return {
        "cycle_seconds": int(sum(greens) + total_lost),
        "total_lost": total_lost,
        "y_sum": round(y_sum, 4),
        "oversaturated": oversaturated,
        "phases": result_phases,
    }


def congestion_level(saturation: float) -> int:
    """按饱和度 v/c 分四级：0 自由流 / 1 缓行 / 2 拥堵 / 3 严重拥堵"""
    if saturation < CONGESTION_THRESHOLDS[0]:
        return 0
    if saturation < CONGESTION_THRESHOLDS[1]:
        return 1
    if saturation < CONGESTION_THRESHOLDS[2]:
        return 2
    return 3


def speed_by_saturation(base_speed: float, saturation: float) -> float:
    """按饱和度推算平均车速（经验曲线，种子数据与模拟任务共用）"""
    factor = max(0.12, 1.0 - 0.78 * saturation ** 1.8)
    return round(max(8.0, base_speed * factor), 1)


def calc_parking_fee(
    minutes: float,
    free_minutes: int,
    first_hour_fee: float,
    hourly_fee: float,
    daily_cap: float,
) -> float:
    """停车计费（纯函数，分钟入参便于测试）。

    规则：免费时长内 0 元；超出部分首小时按首小时费、之后每小时按小时费
    （不足 1 小时按 1 小时计）；每满 24 小时按单日封顶另计一段。
    """
    total = float(minutes)
    if total <= 0:
        return 0.0
    full_days = int(total // 1440)
    remainder = total - full_days * 1440
    fee = full_days * float(daily_cap)
    if remainder > free_minutes:
        billable_hours = math.ceil((remainder - free_minutes) / 60.0)
        fee += min(float(first_hour_fee) + (billable_hours - 1) * float(hourly_fee), float(daily_cap))
    return round(fee, 2)


def calc_parking_fee_dt(
    enter, exit_time, free_minutes: int, first_hour_fee: float, hourly_fee: float, daily_cap: float
) -> float:
    """计费的时间入参包装（datetime 对象）"""
    if exit_time is None or enter is None:
        return 0.0
    minutes = (exit_time - enter).total_seconds() / 60.0
    return calc_parking_fee(minutes, free_minutes, first_hour_fee, hourly_fee, daily_cap)


def hour_flow_rate(
    hour: float, section_factor: float = 1.0, weekday: int = 1, rand_value: float | None = None
) -> float:
    """按附录 D.3 形态生成某小时的理论流率（供模拟任务使用；小时粒度中位）。

    平峰基线 300-600；早晚高峰（7:30-9:00/17:30-19:00）峰值 1500-2200；
    夜间 23:00-5:00 为 50-150；噪声 ±10%；周五晚高峰 ×1.15；周末高峰 ×0.6。
    rand_value 由调用方传入 [0,1) 随机数（保证可测试性）。
    """
    import random as _random

    if 23.0 <= hour or hour < 5.0:
        base = 100.0  # 夜间中位
    else:
        base = 450.0  # 平峰中位
    amp = 1700.0 * section_factor
    if weekday >= 5:
        amp *= 0.6
    morning = amp * math.exp(-((hour - 8.25) / 0.8) ** 2) if 5.0 <= hour < 12.0 else 0.0
    evening = amp * math.exp(-((hour - 18.25) / 0.8) ** 2) if 15.0 <= hour < 22.0 else 0.0
    if weekday == 4:
        evening *= 1.15
    noise = rand_value if rand_value is not None else _random.uniform(0.9, 1.1)
    return (base + morning + evening) * section_factor * noise
