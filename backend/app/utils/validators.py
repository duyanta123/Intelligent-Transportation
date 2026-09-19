"""工具：车牌号校验（支持新能源 8 位牌）、统一分页参数"""
import re

# 省份简称 + 发牌机关字母 + 5 位序号（普通 7 位）或 D/F + 5 位序号（新能源 8 位）
_PROVINCES = "京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云陕甘青蒙藏宁新"
PLATE_RE = re.compile(rf"^[{_PROVINCES}][A-HJ-NP-Z][A-HJ-NP-Z0-9]{{4,6}}$")

UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
UPLOAD_MAX_BYTES = 5 * 1024 * 1024  # 5MB


def is_valid_plate(plate: str) -> bool:
    return bool(PLATE_RE.match((plate or "").strip().upper()))


def normalize_plate(plate: str) -> str:
    return (plate or "").strip().upper()


def clamp_page(page: int, size: int) -> tuple[int, int]:
    page = max(1, int(page or 1))
    size = min(100, max(1, int(size or 10)))
    return page, size
