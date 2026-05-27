"""
P0: 自修改安全引擎 — 防止 agent 自我修改时破坏关键系统

机制：
  1. 代码变更前扫描 diff，检测危险模式
  2. 文件级保护：核心文件禁止删除/覆盖
  3. 命令黑名单：禁止执行破坏性 shell 命令
  4. 变更回滚：记录变更快照，可一键回退
"""

import os
import re
import json
import time
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, ".memory", "snapshots")
AUDIT_LOG = os.path.join(BASE_DIR, ".memory", "safety_audit.json")

# 受保护的核心文件 — 不可删除、不可整体覆盖
PROTECTED_FILES = {
    "main.py",
    "agent.py",
    "config.py",
    "self_learning.py",
    "skill_engine.py",
    "memory_store.py",
    "persona_manager.py",
    "intent_engine.py",
    "self_modify_safety.py",
    "workflow_state.py",
    "observation_engine.py",
    "adaptation_engine.py",
    "skill_gap.py",
    "skill_validator.py",
    "desktop_replay.py",
    "tools/__init__.py",
}

# 危险 shell 命令模式
DANGEROUS_COMMANDS = [
    r"rm\s+-rf\s+[/~]",           # rm -rf / or ~
    r"rm\s+-rf\s+\.",             # rm -rf .
    r"mkfs",                      # 格式化磁盘
    r"dd\s+if=.*of=/dev/",        # dd 写磁盘
    r":(){ :\|:& };:",            # fork bomb
    r"chmod\s+-R\s+777\s+/",     # 全局权限
    r"curl.*\|\s*sh",             # curl pipe to shell
    r"curl.*\|\s*bash",
    r"wget.*\|\s*sh",
    r"wget.*\|\s*bash",
    r"git\s+push\s+.*--force.*main",  # force push main
    r"git\s+push\s+.*--force.*master",
    r"git\s+reset\s+--hard",          # 丢失未提交更改
    r"taskkill.*\/F.*\/IM\s+system",  # 杀系统进程
]

# 危险代码模式（Python）
DANGEROUS_CODE_PATTERNS = [
    (r"__import__\s*\(\s*['\"]os['\"]", "动态导入 os 模块"),
    (r"eval\s*\(", "使用 eval() — 任意代码执行"),
    (r"exec\s*\(", "使用 exec() — 任意代码执行"),
    (r"subprocess\.call\s*\(.*shell\s*=\s*True", "shell=True 命令注入风险"),
    (r"os\.system\s*\(", "os.system() — 命令注入风险"),
    (r"open\s*\(.*/etc/passwd", "读取系统密码文件"),
    (r"open\s*\(.*/etc/shadow", "读取系统影子密码"),
    (r"shutil\.rmtree\s*\(/", "删除根目录树"),
    (r"__import__\s*\(\s*['\"]subprocess['\"]", "动态导入 subprocess"),
]


class SafetyLevel:
    SAFE = "safe"
    WARNING = "warning"
    BLOCKED = "blocked"


class SafetyCheck:
    def __init__(self, level: str, message: str, details: str = ""):
        self.level = level
        self.message = message
        self.details = details

    def to_dict(self):
        return {"level": self.level, "message": self.message, "details": self.details}


def check_command(command: str) -> list[SafetyCheck]:
    """检查 shell 命令是否安全"""
    checks = []
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, command, re.IGNORECASE):
            checks.append(SafetyCheck(
                SafetyLevel.BLOCKED,
                f"危险命令被拦截",
                f"匹配模式: {pattern}",
            ))
    return checks


def check_code_diff(diff_text: str) -> list[SafetyCheck]:
    """检查代码 diff 中是否有危险模式"""
    checks = []
    added_lines = []
    for line in diff_text.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            added_lines.append(line[1:])

    added_text = "\n".join(added_lines)

    for pattern, desc in DANGEROUS_CODE_PATTERNS:
        if re.search(pattern, added_text):
            checks.append(SafetyCheck(
                SafetyLevel.WARNING,
                f"代码安全警告: {desc}",
                f"模式: {pattern}",
            ))

    return checks


def check_file_operation(filepath: str, operation: str) -> SafetyCheck:
    """检查文件操作是否安全"""
    rel = os.path.relpath(filepath, BASE_DIR).replace("\\", "/")

    # 检查是否是受保护文件
    for protected in PROTECTED_FILES:
        if rel == protected or rel.endswith("/" + protected):
            if operation == "delete":
                return SafetyCheck(
                    SafetyLevel.BLOCKED,
                    f"受保护文件不可删除: {rel}",
                    f"核心文件 {protected} 受安全引擎保护",
                )
            if operation == "overwrite":
                return SafetyCheck(
                    SafetyLevel.WARNING,
                    f"覆盖受保护文件: {rel}",
                    "建议使用 Edit 工具进行增量修改而非整体覆盖",
                )

    # 检查是否尝试写入系统目录
    if filepath.startswith(("/", "~")) and not filepath.startswith(BASE_DIR):
        return SafetyCheck(
            SafetyLevel.BLOCKED,
            f"禁止写入项目外路径: {filepath}",
        )

    return SafetyCheck(SafetyLevel.SAFE, "OK")


def create_snapshot(files: list[str] | None = None) -> str:
    """创建当前状态快照，返回快照 ID"""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    snap_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snap_dir = os.path.join(SNAPSHOT_DIR, snap_id)
    os.makedirs(snap_dir, exist_ok=True)

    if files is None:
        # 默认快照核心文件
        files = list(PROTECTED_FILES)

    snapshot_meta = {
        "id": snap_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for f in files:
        src = os.path.join(BASE_DIR, f)
        if not os.path.isfile(src):
            continue
        dst = os.path.join(snap_dir, f.replace("/", "__"))
        try:
            shutil.copy2(src, dst)
            with open(src, "rb") as fh:
                md5 = hashlib.md5(fh.read()).hexdigest()
            snapshot_meta["files"].append({"name": f, "md5": md5})
        except Exception:
            pass

    meta_path = os.path.join(snap_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(snapshot_meta, f, ensure_ascii=False, indent=2)

    _log_audit("snapshot", {"snapshot_id": snap_id, "file_count": len(snapshot_meta["files"])})
    return snap_id


def restore_snapshot(snap_id: str) -> dict:
    """从快照恢复文件"""
    snap_dir = os.path.join(SNAPSHOT_DIR, snap_id)
    meta_path = os.path.join(snap_dir, "meta.json")

    if not os.path.isfile(meta_path):
        return {"error": f"快照 {snap_id} 不存在"}

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    restored = []
    errors = []
    for entry in meta.get("files", []):
        fname = entry["name"]
        src = os.path.join(snap_dir, fname.replace("/", "__"))
        dst = os.path.join(BASE_DIR, fname)
        if not os.path.isfile(src):
            errors.append(f"{fname}: 快照文件缺失")
            continue
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            restored.append(fname)
        except Exception as e:
            errors.append(f"{fname}: {e}")

    _log_audit("restore", {"snapshot_id": snap_id, "restored": len(restored), "errors": len(errors)})
    return {"snapshot_id": snap_id, "restored": restored, "errors": errors}


def list_snapshots() -> list[dict]:
    """列出所有快照"""
    if not os.path.isdir(SNAPSHOT_DIR):
        return []
    snapshots = []
    for d in sorted(os.listdir(SNAPSHOT_DIR), reverse=True):
        meta_path = os.path.join(SNAPSHOT_DIR, d, "meta.json")
        if os.path.isfile(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            snapshots.append({
                "id": meta.get("id", d),
                "timestamp": meta.get("timestamp", ""),
                "file_count": len(meta.get("files", [])),
            })
    return snapshots


def full_safety_check(command: str = "", diff: str = "", filepath: str = "", operation: str = "") -> dict:
    """综合安全检查"""
    all_checks = []
    blocked = False

    if command:
        cmd_checks = check_command(command)
        all_checks.extend(cmd_checks)
        if any(c.level == SafetyLevel.BLOCKED for c in cmd_checks):
            blocked = True

    if diff:
        diff_checks = check_code_diff(diff)
        all_checks.extend(diff_checks)

    if filepath:
        file_check = check_file_operation(filepath, operation)
        all_checks.append(file_check)
        if file_check.level == SafetyLevel.BLOCKED:
            blocked = True

    result = {
        "safe": not blocked,
        "blocked": blocked,
        "checks": [c.to_dict() for c in all_checks],
        "check_count": len(all_checks),
        "warning_count": sum(1 for c in all_checks if c.level == SafetyLevel.WARNING),
        "blocked_count": sum(1 for c in all_checks if c.level == SafetyLevel.BLOCKED),
    }

    if all_checks:
        _log_audit("check", result)

    return result


def _log_audit(action: str, data: dict):
    """记录安全审计日志"""
    os.makedirs(os.path.dirname(AUDIT_LOG), exist_ok=True)
    logs = []
    if os.path.isfile(AUDIT_LOG):
        try:
            with open(AUDIT_LOG, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except (json.JSONDecodeError, Exception):
            logs = []

    entry = {
        "action": action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }
    logs.append(entry)

    # 只保留最近 500 条
    if len(logs) > 500:
        logs = logs[-500:]

    with open(AUDIT_LOG, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def get_audit_log(limit: int = 50) -> list[dict]:
    """获取安全审计日志"""
    if not os.path.isfile(AUDIT_LOG):
        return []
    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs[-limit:]
    except (json.JSONDecodeError, Exception):
        return []
