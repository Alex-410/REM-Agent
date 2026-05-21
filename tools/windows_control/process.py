"""Windows 控制工具 — 进程管理"""
import sys
import os
import subprocess

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


def _check():
    if sys.platform != "win32":
        return {"error": "进程管理仅支持 Windows"}
    return None


def process_list(filter_keyword: str = "") -> dict:
    """列出运行中的进程。可选按关键词过滤。"""
    err = _check()
    if err:
        return err
    if not HAS_PSUTIL:
        return {"error": "psutil 未安装。pip install psutil"}

    try:
        processes = []
        for proc in psutil.process_iter(["pid", "name", "status", "memory_info"]):
            try:
                pinfo = proc.info
                name = pinfo["name"] or ""
                if filter_keyword and filter_keyword.lower() not in name.lower():
                    continue
                processes.append({
                    "pid": pinfo["pid"],
                    "name": name,
                    "status": pinfo["status"],
                    "memory_mb": round(pinfo["memory_info"].rss / 1024 / 1024, 1) if pinfo["memory_info"] else 0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        processes.sort(key=lambda p: -p["memory_mb"])
        return {
            "success": True,
            "count": len(processes),
            "processes": processes[:50],
        }
    except Exception as e:
        return {"error": f"获取进程列表失败: {str(e)}"}


def process_find(name: str) -> dict:
    """按名称查找进程"""
    return process_list(filter_keyword=name)


def process_launch(path: str, args: str = "", wait: bool = False) -> dict:
    """启动一个程序"""
    err = _check()
    if err:
        return err

    try:
        cmd = [path]
        if args:
            cmd.extend(args.split())

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

        if wait:
            stdout, stderr = proc.communicate(timeout=30)
            return {
                "success": True,
                "pid": proc.pid,
                "return_code": proc.returncode,
                "stdout": stdout.decode("gbk", errors="ignore")[:1000],
                "stderr": stderr.decode("gbk", errors="ignore")[:500],
            }

        return {"success": True, "pid": proc.pid, "message": f"已启动 {path}"}
    except FileNotFoundError:
        return {"error": f"找不到程序: {path}。请检查路径是否正确。"}
    except Exception as e:
        return {"error": f"启动失败: {str(e)}"}


def process_kill(pid: int | None = None, name: str | None = None) -> dict:
    """终止进程。按 PID 或名称。"""
    err = _check()
    if err:
        return err
    if not HAS_PSUTIL:
        return {"error": "psutil 未安装。pip install psutil"}

    try:
        killed = []
        if pid:
            proc = psutil.Process(pid)
            proc.terminate()
            killed.append({"pid": pid, "name": proc.name()})

        if name:
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    if name.lower() in (proc.info["name"] or "").lower():
                        proc.terminate()
                        killed.append({"pid": proc.info["pid"], "name": proc.info["name"]})
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        if not killed:
            return {"error": f"未找到匹配的进程"}

        return {"success": True, "killed": killed}
    except Exception as e:
        return {"error": f"终止进程失败: {str(e)}"}


def process_is_running(name: str) -> dict:
    """检查程序是否正在运行"""
    err = _check()
    if err:
        return err
    if not HAS_PSUTIL:
        return {"error": "psutil 未安装。pip install psutil"}

    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if name.lower() in (proc.info["name"] or "").lower():
                    return {"success": True, "running": True, "pid": proc.info["pid"]}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return {"success": True, "running": False}
    except Exception as e:
        return {"error": f"检查失败: {str(e)}"}
