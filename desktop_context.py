"""
桌面环境感知 — 收集当前系统状态供意图引擎参考
"""

import platform
import os


def get_active_window() -> dict:
    """获取当前活跃窗口信息"""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(hwnd)
        _, _, x, y, w, h = win32gui.GetWindowRect(hwnd)
        return {
            "title": title,
            "position": {"x": x, "y": y, "width": w - x, "height": h - y},
        }
    except ImportError:
        return {"error": "win32gui not available"}
    except Exception as e:
        return {"error": str(e)}


def get_running_processes(keywords: list[str] | None = None) -> list[dict]:
    """获取正在运行的进程，可按关键词过滤"""
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name"]):
            try:
                procs.append({"pid": p.info["pid"], "name": p.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if keywords:
            kw_lower = [k.lower() for k in keywords]
            procs = [p for p in procs if any(k in p["name"].lower() for k in kw_lower)]

        return sorted(procs, key=lambda x: x["name"].lower())
    except ImportError:
        return []
    except Exception as e:
        return [{"error": str(e)}]


def get_screen_info() -> dict:
    """获取屏幕信息"""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return {"width": w, "height": h, "available": True}
    except ImportError:
        return {"error": "pyautogui not available", "available": False}
    except Exception as e:
        return {"error": str(e), "available": False}


def get_installed_software() -> list[str]:
    """检测常见软件是否已安装"""
    if platform.system() != "Windows":
        return []

    checks = {
        "WeChat": [
            os.path.expandvars(r"%ProgramFiles%\Tencent\WeChat\WeChat.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\WeChat\WeChat.exe"),
        ],
        "QQ": [
            os.path.expandvars(r"%ProgramFiles%\Tencent\QQ\Bin\QQ.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Tencent\QQ\Bin\QQ.exe"),
        ],
        "Chrome": [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ],
        "VS Code": [
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
        ],
        "Edge": [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        ],
        "Notepad": ["C:\\Windows\\System32\\notepad.exe"],
        "Calculator": ["C:\\Windows\\System32\\calc.exe"],
        "Spotify": [
            os.path.expandvars(r"%AppData%\Spotify\Spotify.exe"),
        ],
    }

    installed = []
    for name, paths in checks.items():
        for path in paths:
            if os.path.isfile(path):
                installed.append(name)
                break
    return sorted(installed)


def collect_context() -> dict:
    """收集完整的桌面环境上下文"""
    context = {
        "os": f"{platform.system()} {platform.release()}",
        "screen": get_screen_info(),
        "active_window": get_active_window(),
        "installed_software": get_installed_software(),
    }

    running = get_running_processes(
        ["wechat", "qq", "chrome", "code", "notepad", "spotify", "微信"]
    )
    if running:
        context["running_processes"] = [p["name"] for p in running if "name" in p]

    return context


def describe_desktop() -> str:
    """返回适合 LLM 阅读的桌面环境描述"""
    ctx = collect_context()

    lines = ["## 当前桌面环境"]
    lines.append(f"操作系统：{ctx['os']}")

    screen = ctx.get("screen", {})
    if "width" in screen and screen.get("available"):
        lines.append(f"屏幕分辨率：{screen['width']}x{screen['height']}")

    aw = ctx.get("active_window", {})
    if "title" in aw and aw["title"]:
        lines.append(f"当前活跃窗口：{aw['title']}")

    sw = ctx.get("installed_software", [])
    if sw:
        lines.append(f"已安装的软件：{', '.join(sw)}")

    rp = ctx.get("running_processes", [])
    if rp:
        lines.append(f"当前正在运行：{', '.join(rp)}")

    return "\n".join(lines)


if __name__ == "__main__":
    print(describe_desktop())
