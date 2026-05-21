"""Windows 控制工具 — 键盘操作"""
import sys
import time

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


def _check():
    if not HAS_PYAUTOGUI:
        return {"error": "pyautogui 未安装。pip install pyautogui"}
    if sys.platform != "win32":
        return {"error": "键盘控制仅支持 Windows"}
    return None


# 常用快捷键映射（中文名 → 按键名）
HOTKEY_MAP = {
    "复制": "ctrl+c",
    "粘贴": "ctrl+v",
    "剪切": "ctrl+x",
    "全选": "ctrl+a",
    "保存": "ctrl+s",
    "撤销": "ctrl+z",
    "重做": "ctrl+y",
    "查找": "ctrl+f",
    "新建": "ctrl+n",
    "关闭": "alt+f4",
    "切换窗口": "alt+tab",
    "打开任务管理器": "ctrl+shift+esc",
    "锁屏": "win+l",
    "打开资源管理器": "win+e",
    "运行": "win+r",
    "截图": "win+shift+s",
    "打开设置": "win+i",
    "桌面": "win+d",
    "搜索": "win+s",
}


def keyboard_type(text: str, interval: float = 0.05) -> dict:
    """输入文字"""
    err = _check()
    if err:
        return err
    try:
        pyautogui.typewrite(text, interval=interval)
        return {"success": True, "chars": len(text)}
    except Exception as e:
        return {"error": f"键盘输入失败: {str(e)}"}


def keyboard_hotkey(keys: str) -> dict:
    """按下快捷键。格式：'ctrl+c', 'alt+tab', 'win+r' 或中文名如 '保存'"""
    err = _check()
    if err:
        return err

    # 中文映射
    if keys in HOTKEY_MAP:
        keys = HOTKEY_MAP[keys]

    try:
        # 拆分组合键
        key_list = keys.lower().split("+")
        pyautogui.hotkey(*key_list)
        return {"success": True, "keys": keys}
    except Exception as e:
        return {"error": f"快捷键失败: {str(e)}"}


def keyboard_press(key: str, duration: float = 0.1) -> dict:
    """按住再释放一个键"""
    err = _check()
    if err:
        return err
    try:
        pyautogui.keyDown(key)
        time.sleep(duration)
        pyautogui.keyUp(key)
        return {"success": True, "key": key}
    except Exception as e:
        return {"error": f"按键失败: {str(e)}"}


def keyboard_write_enter(text: str) -> dict:
    """输入文字后按回车"""
    err = _check()
    if err:
        return err
    try:
        pyautogui.typewrite(text, interval=0.03)
        pyautogui.press("enter")
        return {"success": True, "text": text}
    except Exception as e:
        return {"error": f"输入失败: {str(e)}"}


def get_hotkey_list() -> dict:
    """获取所有可用的中文快捷键列表"""
    return {"success": True, "hotkeys": list(HOTKEY_MAP.keys())}
