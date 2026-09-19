"""车牌识别服务：HyperLPR3（onnxruntime CPU），首次调用自动下载模型并缓存

降级约定：模型加载/推理失败（含网络不通、超时 10 秒）一律返回可识别的
错误响应，前端引导"手动录入车牌"。模型文件约 10MB，缓存在用户目录 .hyperlpr3/。
"""
import concurrent.futures
import threading

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="lpr")
_lock = threading.Lock()
_catcher = None
_init_failed = False

LPR_TIMEOUT_SECONDS = 10


def _get_catcher():
    """懒加载 HyperLPR3 模型（首次运行自动下载约 10MB 模型文件）"""
    global _catcher, _init_failed
    if _catcher is not None:
        return _catcher
    with _lock:
        if _catcher is None and not _init_failed:
            try:
                import hyperlpr3 as lpr3

                _catcher = lpr3.LicensePlateCatcher()
            except Exception:
                _init_failed = True
    return _catcher


def _run_recognize(image_bytes: bytes) -> list[tuple]:
    import io as _io

    import numpy as np
    from PIL import Image

    catcher = _get_catcher()
    if catcher is None:
        raise RuntimeError("车牌识别模型不可用")
    pil = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
    frame = np.array(pil)
    results = catcher(frame)
    # HyperLPR3 返回：[x1,y1,x2,y2, 车牌号, 置信度, 牌类型, 边框索引]
    plates = []
    for item in results:
        if len(item) >= 6:
            plates.append((str(item[4]), float(item[5])))
    return plates


def recognize_plate(image_bytes: bytes) -> dict:
    """识别车牌：10 秒超时保护；失败抛 RuntimeError（调用方转为降级响应）"""
    future = _executor.submit(_run_recognize, image_bytes)
    plates = future.result(timeout=LPR_TIMEOUT_SECONDS)
    if not plates:
        raise RuntimeError("未识别到车牌")
    best_plate, best_conf = max(plates, key=lambda x: x[1])
    return {"plate_no": best_plate, "confidence": round(best_conf, 4)}
