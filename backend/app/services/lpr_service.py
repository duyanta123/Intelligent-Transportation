# -*- coding: utf-8 -*-
"""车牌识别服务：HyperLPR3（onnxruntime CPU），首次运行自动下载模型并缓存

降级约定：模型加载/推理失败（含网络不通、超时 10 秒）一律返回可识别的
错误响应，前端引导"手动录入车牌"。模型文件约 12MB，缓存在用户目录。
策略：应用启动时后台预热模型（不阻塞启动），请求侧总超时 10 秒保护；
预热失败会在下次请求时自动重试，网络恢复后无需重启服务。
"""
import concurrent.futures
import threading

_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="lpr")
_lock = threading.Lock()
_catcher = None
_init_error: Exception | None = None
_init_done = threading.Event()

LPR_TIMEOUT_SECONDS = 10


def _init_catcher():
    global _catcher, _init_error
    with _lock:
        if _catcher is None:
            try:
                import hyperlpr3 as lpr3

                _catcher = lpr3.LicensePlateCatcher()
            except Exception as err:  # 网络/依赖异常均可重试
                _init_error = err
        _init_done.set()


def preload_async():
    """应用启动时调用：后台线程预热模型（首次运行自动下载约 12MB）"""
    _init_done.clear()
    threading.Thread(target=_init_catcher, daemon=True).start()


def _run_recognize(image_bytes: bytes) -> list[tuple]:
    import io as _io

    import numpy as np
    from PIL import Image

    if _catcher is None:
        raise RuntimeError("车牌识别模型不可用")
    pil = Image.open(_io.BytesIO(image_bytes)).convert("RGB")
    frame = np.array(pil)
    results = _catcher(frame)
    # HyperLPR3 返回格式：[车牌号, 置信度, 牌类型索引, [x1,y1,x2,y2]]
    plates = []
    for item in results:
        if len(item) >= 2:
            plates.append((str(item[0]), float(item[1])))
    return plates


def recognize_plate(image_bytes: bytes) -> dict:
    """识别车牌：含模型就绪等待，总超时 10 秒；失败抛 RuntimeError（调用方转为降级响应）"""
    # 等待模型预热（首次含下载时间）
    if not _init_done.wait(timeout=LPR_TIMEOUT_SECONDS):
        preload_async()  # 触发后台重试，本次请求走降级
        raise RuntimeError("车牌识别模型尚未就绪（首次下载约 12MB）")
    if _catcher is None:
        preload_async()
        raise RuntimeError(f"车牌识别模型不可用：{_init_error}")
    future = _executor.submit(_run_recognize, image_bytes)
    plates = future.result(timeout=LPR_TIMEOUT_SECONDS)
    if not plates:
        raise RuntimeError("未识别到车牌")
    best_plate, best_conf = max(plates, key=lambda x: x[1])
    return {"plate_no": best_plate, "confidence": round(best_conf, 4)}
