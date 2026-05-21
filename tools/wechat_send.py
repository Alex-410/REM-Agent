"""
微信自动化 — 联系人搜索 → 发送文本 / 文件
"""

import sys
import time
import pyautogui

# 防止鼠标乱跑时中断
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3


def _ensure_wechat() -> dict | None:
    """确保微信已打开，返回窗口信息"""
    try:
        import win32gui
        import win32con
        import ctypes
    except ImportError:
        return {"error": "pywin32 未安装"}

    windows = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            text = win32gui.GetWindowText(hwnd)
            if text and '微信' in text:
                windows.append((hwnd, text))
    win32gui.EnumWindows(callback, None)

    if not windows:
        return {"error": "微信未打开，请先启动微信"}

    hwnd, title = windows[0]

    # 如果最小化则恢复
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        time.sleep(0.3)

    # 将窗口移到可见位置（避免负坐标导致点击到屏幕外）
    rect = win32gui.GetWindowRect(hwnd)
    target_x = max(0, rect[0])
    if rect[0] < 0 or rect[1] < 0:
        ctypes.windll.user32.SetWindowPos(hwnd, 0, max(0, rect[0]), max(0, rect[1]), 0, 0, 0x0001)
        time.sleep(0.3)
        rect = win32gui.GetWindowRect(hwnd)

    # 激活窗口
    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
    time.sleep(1)

    rect = win32gui.GetWindowRect(hwnd)
    return {
        "hwnd": hwnd,
        "title": title,
        "rect": {"x": rect[0], "y": rect[1], "width": rect[2]-rect[0], "height": rect[3]-rect[1]},
        "moved": rect[0] >= 0,
    }


def _calc_pos(win_info: dict, rel_x: float, rel_y: float) -> tuple[int, int]:
    """根据相对比例计算屏幕坐标"""
    rx, ry = win_info["rect"]["x"], win_info["rect"]["y"]
    rw, rh = win_info["rect"]["width"], win_info["rect"]["height"]
    return (int(rx + rw * rel_x), int(ry + rh * rel_y))


def send_text(contact: str, message: str) -> dict:
    """
    给微信联系人发送文本消息。

    流程：激活微信 → 点击搜索(左上) → 输入联系人名 → 点击联系人 → 输入消息 → 回车发送
    """
    win = _ensure_wechat()
    if isinstance(win, dict) and "error" in win:
        return win

    try:
        # Step 1: 点击搜索框（左上区域）
        sx, sy = _calc_pos(win, 0.05, 0.06)
        pyautogui.click(sx, sy)
        time.sleep(0.8)

        # Step 2: 输入联系人名
        pyautogui.write(contact, interval=0.05)
        time.sleep(1.5)

        # Step 3: 点击第一个搜索结果（列表第一项）
        lx, ly = _calc_pos(win, 0.05, 0.15)
        pyautogui.click(lx, ly)
        time.sleep(1)

        # Step 4: 在输入框输入消息
        tx, ty = _calc_pos(win, 0.6, 0.85)
        pyautogui.click(tx, ty)
        time.sleep(0.5)
        pyautogui.write(message, interval=0.03)

        # Step 5: 回车发送
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)

        return {"success": True, "contact": contact, "message": message[:50]}
    except Exception as e:
        return {"error": f"发送失败: {str(e)}"}


def send_file(contact: str, file_path: str) -> dict:
    """
    给微信联系人发送文件。

    流程：激活微信 → 点击搜索 → 输入联系人 → 点击联系人
          → 点击文件按钮 → 选择文件 → 发送
    """
    win = _ensure_wechat()
    if isinstance(win, dict) and "error" in win:
        return win

    import os
    if not os.path.isfile(file_path):
        return {"error": f"文件不存在: {file_path}"}

    try:
        # Step 1: 搜索联系人
        sx, sy = _calc_pos(win, 0.05, 0.06)
        pyautogui.click(sx, sy)
        time.sleep(0.8)
        pyautogui.write(contact, interval=0.05)
        time.sleep(1.5)

        # Step 2: 点击联系人
        lx, ly = _calc_pos(win, 0.05, 0.15)
        pyautogui.click(lx, ly)
        time.sleep(1)

        # Step 3: 点击 + 或 文件按钮（输入框附近左侧）
        # WeChat PC 版：文件按钮通常在输入框左侧
        fx, fy = _calc_pos(win, 0.33, 0.82)
        pyautogui.click(fx, fy)
        time.sleep(1)

        # Step 4: 在弹出的菜单中选择"文件"
        # 菜单选项通常位于文件按钮附近（正上方或右侧）
        mx, my = _calc_pos(win, 0.35, 0.70)
        pyautogui.click(mx, my)
        time.sleep(1.5)

        # Step 5: 在文件选择对话框中输入文件路径
        # Windows 文件选择对话框：路径输入框通常需要 Ctrl+L 或 Alt+D
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyautogui.write(file_path, interval=0.02)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("enter")  # 确认选择
        time.sleep(1)

        # Step 6: 点击发送
        snd_x, snd_y = _calc_pos(win, 0.6, 0.85)
        pyautogui.click(snd_x, snd_y)
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(0.5)

        return {"success": True, "contact": contact, "file": file_path}
    except Exception as e:
        return {"error": f"发送文件失败: {str(e)}"}


if __name__ == "__main__":
    # 测试发送文本
    result = send_text("rem", "你好")
    print(result)
