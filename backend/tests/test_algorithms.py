"""核心算法单元测试：Webster 配时、拥堵分级、停车计费、流量形态（纯函数，不碰数据库）"""
import math
from datetime import datetime

import pytest

from app.services.algorithms import (
    CAPACITY_PER_LANE,
    CONGESTION_THRESHOLDS,
    SATURATION_FLOW,
    calc_parking_fee,
    calc_parking_fee_dt,
    congestion_level,
    hour_flow_rate,
    speed_by_saturation,
    webster_calc,
)


# ---------------- Webster 配时 ----------------
def _phases(*flows):
    return [{"name": f"相位{i + 1}", "flow": f, "lanes": 2} for i, f in enumerate(flows)]


class TestWebster:
    def test_cycle_in_clamp_range(self):
        result = webster_calc(_phases(800, 600, 500, 400))
        assert 40 <= result["cycle_seconds"] <= 180
        assert not result["oversaturated"]

    def test_green_time_equals_cycle_minus_lost(self):
        result = webster_calc(_phases(900, 700, 500, 300))
        greens = sum(p["green"] for p in result["phases"])
        assert greens + result["total_lost"] == result["cycle_seconds"]

    def test_higher_flow_gets_longer_green(self):
        # 流量比 0.667 : 0.167，周期足够长（约 138s），绿灯严格按流量比分配
        result = webster_calc(_phases(2400, 600))
        greens = [p["green"] for p in result["phases"]]
        assert greens[0] > greens[1] * 2

    def test_min_green_enforced(self):
        # 一个相位流量极小，仍应保证最短绿灯 15 秒
        result = webster_calc([{"name": "主", "flow": 1500, "lanes": 2}, {"name": "次", "flow": 30, "lanes": 1}])
        assert all(p["green"] >= 15 for p in result["phases"])

    def test_oversaturated_clamps_to_max_cycle(self):
        result = webster_calc(_phases(3000, 3200, 2800, 2900))
        assert result["oversaturated"]
        assert result["cycle_seconds"] == 180

    def test_reject_zero_flow(self):
        with pytest.raises(ValueError):
            webster_calc([{"name": "A", "flow": 0, "lanes": 2}])

    def test_reject_empty_phases(self):
        with pytest.raises(ValueError):
            webster_calc([])

    def test_flow_ratio_formula(self):
        # y = q / (s * n)：单相位 y_i 校验
        result = webster_calc([{"name": "A", "flow": 900, "lanes": 1}])
        assert result["phases"][0]["y"] == round(900 / SATURATION_FLOW, 4)


# ---------------- 拥堵分级 ----------------
class TestCongestion:
    def test_free_flow(self):
        assert congestion_level(0.1) == 0
        assert congestion_level(0.39) == 0

    def test_slow(self):
        assert congestion_level(0.4) == 1
        assert congestion_level(0.69) == 1

    def test_congested(self):
        assert congestion_level(0.7) == 2
        assert congestion_level(0.89) == 2

    def test_severe(self):
        assert congestion_level(0.9) == 3
        assert congestion_level(1.2) == 3

    def test_thresholds_match_spec(self):
        assert CONGESTION_THRESHOLDS == (0.4, 0.7, 0.9)


# ---------------- 车速模型 ----------------
class TestSpeed:
    def test_speed_decreases_with_saturation(self):
        assert speed_by_saturation(50, 0.2) > speed_by_saturation(50, 0.8)

    def test_speed_floor(self):
        assert speed_by_saturation(50, 1.2) >= 8.0

    def test_capacity_per_lane(self):
        assert CAPACITY_PER_LANE == 600


# ---------------- 停车计费 ----------------
class TestParkingFee:
    def test_within_free_period(self):
        assert calc_parking_fee(10, 15, 5, 3, 40) == 0.0

    def test_exactly_free_boundary(self):
        assert calc_parking_fee(15, 15, 5, 3, 40) == 0.0

    def test_first_hour_only(self):
        # 免费 15 分钟后 50 分钟 → 计 1 小时 → 首小时 5 元
        assert calc_parking_fee(65, 15, 5, 3, 40) == 5.0

    def test_partial_hour_ceil(self):
        # 免费 15 分钟后 61 分钟 → 计 2 小时 → 5 + 3 = 8 元
        assert calc_parking_fee(76, 15, 5, 3, 40) == 8.0

    def test_daily_cap(self):
        # 连续 10 小时：5 + 9*3 = 32 < 40；再 1 小时 → 5+10*3=35；构造超过封顶
        fee = calc_parking_fee(60 * 20, 0, 5, 3, 40)
        assert fee == 40.0

    def test_multi_day(self):
        # 2 整天 + 1 小时：2*40 + 5 = 85
        assert calc_parking_fee(1440 * 2 + 60, 0, 5, 3, 40) == 85.0

    def test_dt_wrapper(self):
        enter = datetime(2026, 9, 1, 10, 0, 0)
        exit_time = datetime(2026, 9, 1, 12, 30, 0)
        # 150 分钟，免费 15 → 135 分钟 → 3 小时 → 5 + 2*3 = 11
        assert calc_parking_fee_dt(enter, exit_time, 15, 5, 3, 40) == 11.0

    def test_zero_duration(self):
        now = datetime(2026, 9, 1, 10, 0, 0)
        assert calc_parking_fee_dt(now, now, 15, 5, 3, 40) == 0.0


# ---------------- 流量形态 ----------------
class TestHourFlow:
    def test_morning_peak_shape(self):
        peak = hour_flow_rate(8.25, 1.0, 1, rand_value=1.0)
        night = hour_flow_rate(3.0, 1.0, 1, rand_value=1.0)
        assert peak > 1500
        assert night < 200

    def test_evening_peak_friday_boost(self):
        friday = hour_flow_rate(18.25, 1.0, 4, rand_value=1.0)
        monday = hour_flow_rate(18.25, 1.0, 0, rand_value=1.0)
        assert friday > monday

    def test_weekend_peak_weaker(self):
        weekday = hour_flow_rate(8.25, 1.0, 2, rand_value=1.0)
        weekend = hour_flow_rate(8.25, 1.0, 6, rand_value=1.0)
        assert weekend < weekday

    def test_value_type(self):
        v = hour_flow_rate(10.0, 1.0, 1, rand_value=1.0)
        assert isinstance(v, float)
        assert not math.isnan(v)
