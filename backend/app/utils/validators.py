"""工具：车牌号校验（支持新能源 8 位牌）、统一分页参数、上传内容嗅探、时区归一化"""
import re
from datetime import datetime, timedelta, timezone

# 省份简称 + 发牌机关字母 + 5 位序号（普通 7 位）或 D/F + 5 位序号（新能源 8 位）
_PROVINCES = "京津沪渝冀晋辽吉黑苏浙皖闽赣鲁豫鄂湘粤桂琼川贵云陕甘青蒙藏宁新"
PLATE_RE = re.compile(rf"^[{_PROVINCES}][A-HJ-NP-Z][A-HJ-NP-Z0-9]{{4,6}}$")

UPLOAD_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
UPLOAD_MAX_BYTES = 5 * 1024 * 1024  # 5MB

# 中国（Asia/Shanghai）自 1991 年起无夏令时，固定 UTC+8；
# 用固定偏移避免 Windows 下 zoneinfo 依赖 tzdata 包
_CN_TZ = timezone(timedelta(hours=8))


def is_valid_plate(plate: str) -> bool:
    return bool(PLATE_RE.match((plate or "").strip().upper()))


def normalize_plate(plate: str) -> str:
    return (plate or "").strip().upper()


def clamp_page(page: int, size: int, max_size: int = 100) -> tuple[int, int]:
    page = max(1, int(page or 1))
    size = min(max_size, max(1, int(size or 10)))
    return page, size


def to_local_naive(dt: datetime | None) -> datetime | None:
    """把可能带时区的入参归一化为上海本地 naive 时间。

    库中一律 DATETIME 本地时间；若前端用 toISOString() 传参（Z 结尾），
    PyMySQL 会忽略 tzinfo 直接取墙上时间，造成 8 小时偏移，故入口统一转换。
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(_CN_TZ).replace(tzinfo=None)
    return dt


def is_image_bytes(data: bytes) -> bool:
    """按 magic bytes 校验图片内容，防止任意文件改后缀上传"""
    if len(data) < 12:
        return False
    if data[:3] == b"\xff\xd8\xff":  # JPEG
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":  # PNG
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":  # WebP
        return True
    return False
