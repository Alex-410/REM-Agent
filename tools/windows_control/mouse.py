"""Windows 控制工具 — 鼠标操作（仅在 Windows 上可用）"""
import sys
import time

# 尝试导入，非 Windows 环境跳过
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

SCREEN_WIDTH, SCREEN_HEIGHT = (0, 0)
if HAS_PYAUTOGUI:
    try:
        SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()
    except:
        pass


def _check_available():
    if not HAS_PYAUTOGUI:
        return {"error": "pyautogui 未安装。pip install pyautogui"}
    if sys.platform != "win32":
        return {"error": "鼠标控制仅支持 Windows"}
    return None


def mouse_move(x: int, y: int, duration: float = 0.2) -> dict:
    """移动鼠标到指定坐标"""
    err = _check_available()
    if err:
        return err
    try:
        pyautogui.moveTo(x, y, duration=duration)
        return {"success": True, "position": (x, y)}
    except Exception as e:
        return {"error": f"鼠标移动失败: {str(e)}"}


def mouse_click(x: int | None = None, y: int | None = None,
                button: str = "left", clicks: int = 1) -> dict:
    """在指定位置点击鼠标。不传坐标则在当前位置点击。"""
    err = _check_available()
    if err:
        return err
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, clicks=clicks, button=button)
            pos = (x, y)
        else:
            pyautogui.click(clicks=clicks, button=button)
            pos = pyautogui.position()
        return {"success": True, "position": pos, "button": button, "clicks": clicks}
    except Exception as e:
        return {"error": f"鼠标点击失败: {str(e)}"}


def mouse_double_click(x: int | None = None, y: int | None = None) -> dict:
    """双击"""
    return mouse_click(x, y, clicks=2)


def mouse_right_click(x: int | None = None, y: int | None = None) -> dict:
    """右键点击"""
    return mouse_click(x, y, button="right")


def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int,
               duration: float = 0.5, button: str = "left") -> dict:
    """从起点拖拽到终点"""
    err = _check_available()
    if err:
        return err
    try:
        pyautogui.moveTo(start_x, start_y, duration=0.1)
        pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration, button=button)
        return {
            "success": True,
            "from": (start_x, start_y),
            "to": (end_x, end_y),
        }
    except Exception as e:
        return {"error": f"拖拽失败: {str(e)}"}


def mouse_scroll(clicks: int, x: int | None = None, y: int | None = None) -> dict:
    """滚动鼠标滚轮。正数向上，负数向下。"""
    err = _check_available()
    if err:
        return err
    try:
        if x is not None and y is not None:
            pyautogui.scroll(clicks, x=x, y=y)
        else:
            pyautogui.scroll(clicks)
        return {"success": True, "scroll_clicks": clicks}
    except Exception as e:
        return {"error": f"滚动失败: {str(e)}"}


def mouse_position() -> dict:
    """获取当前鼠标位置"""
    err = _check_available()
    if err:
        return err
    try:
        x, y = pyautogui.position()
        return {"success": True, "x": x, "y": y}
    except Exception as e:
        return {"error": f"获取位置失败: {str(e)}"}


def get_screen_size() -> dict:
    """获取屏幕分辨率"""
    err = _check_available()
    if err:
        return err
    try:
        w, h = pyautogui.size()
        return {"success": True, "width": w, "height": h}
    except Exception as e:
        return {"error": f"获取屏幕信息失败: {str(e)}"}
