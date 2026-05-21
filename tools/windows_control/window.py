"""Windows 控制工具 — 窗口管理"""
import sys
import time
import ctypes

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

HAS_WIN32GUI = False
try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32GUI = True
except ImportError:
    pass

# user32.dll for window operations
_user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def _check():
    if sys.platform != "win32":
        return {"error": "窗口管理仅支持 Windows"}
    if not HAS_WIN32GUI:
        return {"error": "pywin32 未安装。pip install pywin32"}
    return None


def _enum_windows():
    """枚举所有顶级窗口"""
    windows = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        text = win32gui.GetWindowText(hwnd)
        if text:
            try:
                rect = win32gui.GetWindowRect(hwnd)
                windows.append({
                    "hwnd": hwnd,
                    "title": text,
                    "rect": list(rect),
                    "class_name": win32gui.GetClassName(hwnd),
                })
            except:
                pass

    win32gui.EnumWindows(callback, None)
    return windows


def window_list(filter_keyword: str = "") -> dict:
    """列出所有可见窗口。可选按标题关键词过滤。"""
    err = _check()
    if err:
        return err

    try:
        windows = _enum_windows()
        if filter_keyword:
            windows = [w for w in windows if filter_keyword.lower() in w["title"].lower()]

        return {
            "success": True,
            "count": len(windows),
            "windows": windows[:50],
        }
    except Exception as e:
        return {"error": f"获取窗口列表失败: {str(e)}"}


def window_find(title_keyword: str) -> dict:
    """按标题关键词查找窗口"""
    return window_list(filter_keyword=title_keyword)


def window_activate(title_keyword: str) -> dict:
    """激活窗口（让它获得焦点，显示在最前面）"""
    err = _check()
    if err:
        return err

    try:
        windows = _enum_windows()
        target = None
        for w in windows:
            if title_keyword.lower() in w["title"].lower():
                target = w
                break

        if not target:
            return {"error": f"未找到标题包含 '{title_keyword}' 的窗口"}

        hwnd = target["hwnd"]

        # 如果窗口最小化，恢复
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        # 方法1: SwitchToThisWindow（绕开 SetForegroundWindow 限制）
        if _user32:
            _user32.SwitchToThisWindow(hwnd, True)
            time.sleep(0.2)

        # 方法2: 模拟 Alt 按键后 SetForegroundWindow（备选）
        cur_foreground = win32gui.GetForegroundWindow()
        if cur_foreground != hwnd:
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                # Alt 键模拟法
                ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)  # Alt 按下
                time.sleep(0.05)
                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # Alt 释放
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

        time.sleep(0.3)

        return {
            "success": True,
            "window": target,
            "message": f"已激活窗口: {target['title']}",
        }
    except Exception as e:
        return {"error": f"激活窗口失败: {str(e)}"}


def window_close(title_keyword: str) -> dict:
    """关闭窗口"""
    err = _check()
    if err:
        return err

    try:
        windows = _enum_windows()
        target = None
        for w in windows:
            if title_keyword.lower() in w["title"].lower():
                target = w
                break

        if not target:
            return {"error": f"未找到标题包含 '{title_keyword}' 的窗口"}

        win32gui.PostMessage(target["hwnd"], win32con.WM_CLOSE, 0, 0)

        return {
            "success": True,
            "window": target["title"],
            "message": f"已关闭窗口: {target['title']}",
        }
    except Exception as e:
        return {"error": f"关闭窗口失败: {str(e)}"}


def window_minimize(title_keyword: str) -> dict:
    """最小化窗口"""
    err = _check()
    if err:
        return err

    try:
        windows = _enum_windows()
        for w in windows:
            if title_keyword.lower() in w["title"].lower():
                win32gui.ShowWindow(w["hwnd"], win32con.SW_MINIMIZE)
                return {"success": True, "window": w["title"], "message": f"已最小化: {w['title']}"}

        return {"error": f"未找到窗口: {title_keyword}"}
    except Exception as e:
        return {"error": f"最小化失败: {str(e)}"}


def window_get_active() -> dict:
    """获取当前激活的窗口信息"""
    err = _check()
    if err:
        return err

    try:
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        cls = win32gui.GetClassName(hwnd)
        rect = list(win32gui.GetWindowRect(hwnd))
        return {
            "success": True,
            "window": {
                "hwnd": hwnd,
                "title": title,
                "class_name": cls,
                "rect": rect,
            },
        }
    except Exception as e:
        return {"error": f"获取失败: {str(e)}"}
