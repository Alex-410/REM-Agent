"""
桌面操作序列回放 — P3

功能：
  1. 录制：包装现有鼠标/键盘/窗口工具，记录每步操作和时间戳
  2. 存储：JSON 格式保存到 .memory/sequences/
  3. 回放：按顺序执行录制的操作，支持速度调节
  4. 管理：列出、删除、导出序列
"""

import json
import os
import time
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SEQUENCES_DIR = os.path.join(BASE_DIR, ".memory", "sequences")

# 操作名 → 工具函数映射（延迟加载）
_ACTION_MAP: dict[str, Any] = {}
_recording: dict | None = None


def _ensure_dir():
    os.makedirs(SEQUENCES_DIR, exist_ok=True)


def _get_action_map() -> dict:
    """延迟加载工具函数映射"""
    global _ACTION_MAP
    if not _ACTION_MAP:
        from tools.windows_control.mouse import (
            mouse_click, mouse_move, mouse_double_click,
            mouse_right_click, mouse_drag, mouse_scroll,
        )
        from tools.windows_control.keyboard import (
            keyboard_type, keyboard_hotkey, keyboard_press, keyboard_write_enter,
        )
        from tools.windows_control.process import process_launch, process_kill
        from tools.windows_control.window import (
            window_activate, window_close, window_minimize,
        )
        _ACTION_MAP = {
            "mouse_click": mouse_click,
            "mouse_move": mouse_move,
            "mouse_double_click": mouse_double_click,
            "mouse_right_click": mouse_right_click,
            "mouse_drag": mouse_drag,
            "mouse_scroll": mouse_scroll,
            "keyboard_type": keyboard_type,
            "keyboard_hotkey": keyboard_hotkey,
            "keyboard_press": keyboard_press,
            "keyboard_write_enter": keyboard_write_enter,
            "process_launch": process_launch,
            "process_kill": process_kill,
            "window_activate": window_activate,
            "window_close": window_close,
            "window_minimize": window_minimize,
        }
    return _ACTION_MAP


def start_recording(name: str) -> dict:
    """开始录制桌面操作序列"""
    global _recording
    if _recording is not None:
        return {"error": f"已在录制中: {_recording['name']}，请先 stop_recording"}

    _recording = {
        "name": name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": [],
        "start_time": time.monotonic(),
    }
    return {"success": True, "name": name, "message": "录制已开始，执行桌面操作会被记录"}


def record_step(action: str, args: dict) -> dict:
    """记录一个操作步骤（由工具调用时自动触发，也可手动调用）"""
    global _recording
    if _recording is None:
        return {"error": "未在录制中，请先 start_recording"}

    now = time.monotonic()
    delay_ms = int((now - _recording["start_time"]) * 1000) if _recording["steps"] else 0

    step = {
        "action": action,
        "args": args,
        "delay_ms": delay_ms,
        "recorded_at": time.time(),
    }
    _recording["steps"].append(step)

    # 更新下次的起始时间
    _recording["start_time"] = now

    return {"success": True, "step_index": len(_recording["steps"]) - 1, "action": action}


def stop_recording(save: bool = True) -> dict:
    """停止录制，可选保存"""
    global _recording
    if _recording is None:
        return {"error": "未在录制中"}

    result = {
        "name": _recording["name"],
        "steps_count": len(_recording["steps"]),
        "total_duration_ms": sum(s["delay_ms"] for s in _recording["steps"]),
    }

    if save and _recording["steps"]:
        path = _save_sequence(_recording)
        result["saved"] = True
        result["path"] = path
    else:
        result["saved"] = False

    _recording = None
    return result


def _save_sequence(sequence: dict) -> str:
    """保存序列到文件"""
    _ensure_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in sequence["name"])
    filename = f"{safe_name}.json"
    path = os.path.join(SEQUENCES_DIR, filename)

    # 如果同名文件已存在，加数字后缀
    counter = 1
    while os.path.isfile(path):
        filename = f"{safe_name}_{counter}.json"
        path = os.path.join(SEQUENCES_DIR, filename)
        counter += 1

    data = {
        "name": sequence["name"],
        "created_at": sequence["created_at"],
        "steps": sequence["steps"],
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return path


def list_sequences() -> dict:
    """列出所有保存的序列"""
    _ensure_dir()
    sequences = []
    for fname in sorted(os.listdir(SEQUENCES_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(SEQUENCES_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            sequences.append({
                "name": data.get("name", fname),
                "file": fname,
                "steps_count": len(data.get("steps", [])),
                "created_at": data.get("created_at", ""),
                "total_duration_ms": sum(s.get("delay_ms", 0) for s in data.get("steps", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return {"sequences": sequences, "count": len(sequences)}


def get_sequence(name: str) -> dict | None:
    """按名称获取序列"""
    _ensure_dir()
    # 精确匹配
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    for suffix in ["", ".json"]:
        path = os.path.join(SEQUENCES_DIR, safe_name + suffix)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # 模糊匹配
    for fname in os.listdir(SEQUENCES_DIR):
        if not fname.endswith(".json"):
            continue
        if name.lower() in fname.lower():
            with open(os.path.join(SEQUENCES_DIR, fname), "r", encoding="utf-8") as f:
                return json.load(f)

    return None


def delete_sequence(name: str) -> dict:
    """删除一个序列"""
    _ensure_dir()
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    path = os.path.join(SEQUENCES_DIR, safe_name + ".json")
    if not os.path.isfile(path):
        # 模糊匹配
        for fname in os.listdir(SEQUENCES_DIR):
            if name.lower() in fname.lower():
                path = os.path.join(SEQUENCES_DIR, fname)
                break
        else:
            return {"error": f"序列 '{name}' 不存在"}

    os.remove(path)
    return {"success": True, "deleted": name}


def replay_sync(name: str, speed: float = 1.0, dry_run: bool = False) -> dict:
    """同步版本的回放（供工具调用使用）"""
    return _replay_impl(name, speed, dry_run)


async def replay(name: str, speed: float = 1.0, dry_run: bool = False) -> dict:
    """异步版本的回放（供 API 使用）"""
    return _replay_impl(name, speed, dry_run)


def _replay_impl(name: str, speed: float = 1.0, dry_run: bool = False) -> dict:
    """
    回放一个录制的操作序列。

    Args:
        name: 序列名称
        speed: 回放速度倍数（1.0=原速，2.0=2倍速，0.5=半速）
        dry_run: 如果 True，只返回将要执行的步骤，不实际执行
    """
    sequence = get_sequence(name)
    if not sequence:
        return {"error": f"序列 '{name}' 不存在"}

    steps = sequence.get("steps", [])
    if not steps:
        return {"error": "序列为空"}

    if dry_run:
        return {
            "name": sequence["name"],
            "steps_count": len(steps),
            "steps": steps,
            "dry_run": True,
        }

    action_map = _get_action_map()
    results = []
    errors = []

    for i, step in enumerate(steps):
        action = step.get("action", "")
        args = step.get("args", {})
        delay_ms = step.get("delay_ms", 0)

        # 等待（按速度调整）
        if delay_ms > 0 and i > 0:
            wait_sec = (delay_ms / 1000.0) / speed
            time.sleep(min(wait_sec, 5.0))  # 最多等 5 秒

        # 执行操作
        handler = action_map.get(action)
        if not handler:
            errors.append({"step": i, "action": action, "error": f"未知操作: {action}"})
            results.append({"step": i, "action": action, "success": False, "error": "unknown action"})
            continue

        try:
            result = handler(**args)
            success = not result.get("error")
            results.append({"step": i, "action": action, "success": success, "result": result})
            if not success:
                errors.append({"step": i, "action": action, "error": result.get("error", "")})
        except Exception as e:
            errors.append({"step": i, "action": action, "error": str(e)})
            results.append({"step": i, "action": action, "success": False, "error": str(e)})

    return {
        "name": sequence["name"],
        "steps_executed": len(results),
        "errors": len(errors),
        "results": results,
        "speed": speed,
    }


def get_recording_status() -> dict:
    """获取当前录制状态"""
    if _recording is None:
        return {"recording": False}
    return {
        "recording": True,
        "name": _recording["name"],
        "steps_count": len(_recording["steps"]),
        "duration_ms": int((time.monotonic() - _recording["start_time"]) * 1000)
            if _recording["steps"] else 0,
    }


def import_sequence(name: str, steps: list[dict]) -> dict:
    """手动导入一个操作序列（不需要录制）"""
    _ensure_dir()
    sequence = {
        "name": name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "steps": steps,
    }
    path = _save_sequence(sequence)
    return {"success": True, "name": name, "path": path, "steps_count": len(steps)}
