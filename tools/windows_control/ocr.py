"""
屏幕文字识别 (OCR) — 用 easyocr 识别屏幕上的文字（中英文）
"""

import os
import time
import warnings

# 抑制 torchvision 的 numpy 兼容性警告
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")

_OCR_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "images"
)

_reader = None


def _get_reader():
    """懒加载 easyocr Reader，首次调用会下载模型"""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(
            ["ch_sim", "en"],  # 中文简体 + 英文
            gpu=False,         # CPU 模式，兼容性更好
            verbose=False,
        )
    return _reader


def recognize_file(image_path: str) -> dict:
    """
    识别图片文件中的文字。

    返回每个识别结果包含：文字内容、置信度、位置坐标。
    """
    reader = _get_reader()
    start = time.time()
    results = reader.readtext(image_path)
    elapsed = time.time() - start

    items = []
    for bbox, text, confidence in results:
        x1, y1 = bbox[0]  # 左上角
        x2, y2 = bbox[2]  # 右下角
        items.append({
            "text": text,
            "confidence": round(confidence, 3),
            "bbox": {
                "left": int(x1), "top": int(y1),
                "right": int(x2), "bottom": int(y2),
                "width": int(x2 - x1), "height": int(y2 - y1),
            },
        })

    return {
        "success": True,
        "items": items,
        "count": len(items),
        "time_seconds": round(elapsed, 2),
    }


def recognize_screen() -> dict:
    """
    截取全屏后识别文字。

    返回识别结果 + 截图路径。
    """
    from .screenshot import capture_fullscreen
    screen = capture_fullscreen()
    if "error" in screen:
        return screen

    result = recognize_file(screen["file_path"])
    result["screenshot"] = screen
    return result


def recognize_region(left: int, top: int, width: int, height: int) -> dict:
    """
    截取指定区域后识别文字。
    """
    from .screenshot import capture_region
    screen = capture_region(left, top, width, height)
    if "error" in screen:
        return screen

    result = recognize_file(screen["file_path"])
    result["screenshot"] = screen
    return result


def recognize_active_window() -> dict:
    """
    截取当前活跃窗口后识别文字。
    """
    from .screenshot import capture_active_window
    screen = capture_active_window()
    if "error" in screen:
        return screen

    result = recognize_file(screen["file_path"])
    result["screenshot"] = screen
    return result


def find_text_on_screen(target: str) -> dict:
    """
    在屏幕上搜索指定的文字，返回位置和截图。

    可用于：查找按钮位置、确认文字存在性。
    """
    result = recognize_screen()
    if "error" in result:
        return result

    found = []
    for item in result.get("items", []):
        if target.lower() in item["text"].lower():
            found.append(item)

    return {
        "success": len(found) > 0,
        "found": found,
        "count": len(found),
        "screenshot": result.get("screenshot"),
        "all_texts": [i["text"] for i in result.get("items", [])],
    }


def click_text_on_screen(target: str, button: str = "left") -> dict:
    """
    在屏幕上找到指定文字并点击它。

    流程：全屏OCR → 匹配文字 → 计算中心坐标 → 鼠标点击。

    参数：
        target: 要查找并点击的文字
        button: 鼠标按键 (left/right/double)

    返回：
        {"success": True/False, "text": "...", "position": (x,y), ...}
    """
    # 1. OCR 全屏找文字
    result = recognize_screen()
    if "error" in result:
        return {"error": result["error"]}

    # 2. 模糊匹配文字
    target_lower = target.lower()
    matched = None
    for item in result.get("items", []):
        if target_lower in item["text"].lower():
            matched = item
            break

    if not matched:
        return {
            "success": False,
            "error": f"未在屏幕上找到文字 '{target}'",
            "all_texts": [i["text"] for i in result.get("items", [])],
        }

    # 3. 计算中心坐标
    bbox = matched["bbox"]
    center_x = (bbox["left"] + bbox["right"]) // 2
    center_y = (bbox["top"] + bbox["bottom"]) // 2

    # 4. 鼠标点击
    try:
        from .mouse import mouse_click, mouse_move
        # 先移动过去再看，视觉反馈
        move_result = mouse_move(center_x, center_y, duration=0.3)
        if "error" in move_result:
            return {"error": f"鼠标移动失败: {move_result['error']}"}

        import time
        time.sleep(0.2)

        if button == "double":
            click_result = mouse_click(center_x, center_y, clicks=2)
        else:
            click_result = mouse_click(center_x, center_y, button=button)

        if "error" in click_result:
            return {"error": click_result["error"]}
    except Exception as e:
        return {"error": f"点击操作失败: {str(e)}"}

    return {
        "success": True,
        "text": matched["text"],
        "position": (center_x, center_y),
        "confidence": matched["confidence"],
        "bbox": matched["bbox"],
        "button": button,
    }
