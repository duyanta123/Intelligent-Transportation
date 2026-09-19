"""工具：图形验证码生成（存 Redis，TTL 5 分钟）"""
import base64
import io
import random

from captcha.image import ImageCaptcha

# 去掉易混淆字符（0/O、1/I/L）
CAPTCHA_CHARS = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_captcha(length: int = 4) -> tuple[str, str]:
    """生成验证码，返回 (code, data_url)。code 由调用方写入 Redis。"""
    code = "".join(random.choices(CAPTCHA_CHARS, k=length))
    image = ImageCaptcha(width=140, height=48)
    buf = io.BytesIO()
    image.write(code, buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return code, f"data:image/png;base64,{b64}"
