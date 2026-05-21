"""
屏幕截图工具 — 用 mss 实现快速全屏 / 区域截图
"""

import os
import time
from PIL import Image

_SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "output", "images"
)


def _ensure_dir():
    os.makedirs(_SCREENSHOT_DIR, exist_ok=True)


def capture_fullscreen() -> dict:
    """
    截取全屏，保存到 output/images/ 并返回路径和尺寸。
    """
    try:
        import mss
    except ImportError:
        return {"error": "mss 未安装，请 pip install mss"}

    _ensure_dir()
    filename = f"screenshot_{int(time.time())}.png"
    filepath = os.path.join(_SCREENSHOT_DIR, filename)

    with mss.mss() as sct:
        monitor = sct.monitors[1]  # 主显示器
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        img.save(filepath)

    return {
        "success": True,
        "file_path": filepath,
        "width": monitor["width"],
        "height": monitor["height"],
        "filename": filename,
    }


def capture_region(left: int, top: int, width: int, height: int) -> dict:
    """
    截取指定区域。
    """
    try:
        import mss
    except ImportError:
        return {"error": "mss 未安装，请 pip install mss"}

    _ensure_dir()
    filename = f"screenshot_{int(time.time())}.png"
    filepath = os.path.join(_SCREENSHOT_DIR, filename)

    monitor = {"left": left, "top": top, "width": width, "height": height}

    with mss.mss() as sct:
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        img.save(filepath)

    return {
        "success": True,
        "file_path": filepath,
        "width": width,
        "height": height,
        "region": {"left": left, "top": top, "width": width, "height": height},
        "filename": filename,
    }


def capture_active_window() -> dict:
    """
    截取当前活跃窗口。
    """
    try:
        import win32gui
        import win32con
    except ImportError:
        return {"error": "pywin32 未安装"}

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return {"error": "无法获取当前窗口句柄"}

    # 恢复窗口（如果最小化）
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.3)

    rect = win32gui.GetWindowRect(hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    title = win32gui.GetWindowText(hwnd)

    return capture_region(left, top, width, height) | {
        "window_title": title,
    }
